from __future__ import annotations

import asyncio
import json
import secrets
import shutil
import time
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Annotated, Any, Literal
from urllib.parse import urlsplit

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.exceptions import RequestValidationError
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, ConfigDict, Field, StrictBool

from .database import Database, extract_records
from .evolution import EvolutionClient, EvolutionError
from .settings import Settings
from .users import UserDirectory
from .sync import Reconciler
from .photos import PhotoCache
from .evolution import valid_chat


COOKIE = "whatsapp_archive_session"
basic = HTTPBasic(auto_error=False)


class LoginBody(BaseModel):
    username: str = Field(min_length=1, max_length=256)
    password: str = Field(min_length=1, max_length=1024)


class SeenBody(BaseModel):
    chat: str | None = Field(default=None, max_length=2048)
    ids: list[str] | None = Field(default=None, max_length=200)


class ConversationPreferencesBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    chat: str = Field(min_length=1, max_length=2048)
    favorite: StrictBool | None = None
    labels: list[Annotated[str, Field(min_length=1, max_length=64)]] | None = Field(default=None, max_length=20)
    archived_local: StrictBool | None = None


def equal_secret(left: str, right: str) -> bool:
    return secrets.compare_digest(left.encode("utf-8"), right.encode("utf-8"))


def storage_state(settings: Settings) -> dict[str, Any]:
    try:
        free = shutil.disk_usage(settings.data_dir).free
        return {"free_bytes": free, "minimum_free_bytes": settings.minimum_free_bytes, "write_blocked": free < settings.minimum_free_bytes}
    except OSError:
        return {"free_bytes": None, "minimum_free_bytes": settings.minimum_free_bytes, "write_blocked": True}


def require_storage(settings: Settings) -> None:
    if storage_state(settings)["write_blocked"]:
        raise HTTPException(503, detail="storage_below_minimum")


def create_app(settings: Settings | None = None, evolution: EvolutionClient | None = None, start_background: bool = True, photos: PhotoCache | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    settings.validate()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.users = UserDirectory(settings)
        app.state.auth_slots = asyncio.Semaphore(4)
        app.state.db = Database(settings.data_dir / "archive.sqlite3", settings.instance, settings.username)
        app.state.evolution = evolution or EvolutionClient(settings)
        app.state.reconciler = Reconciler(app.state.db, app.state.evolution, settings)
        app.state.photos = photos or PhotoCache(settings, app.state.evolution)
        app.state.login_failures = {}
        periodic_task = asyncio.create_task(app.state.reconciler.periodic()) if start_background else None
        try:
            yield
        finally:
            for task in (periodic_task, app.state.reconciler.task):
                if task and not task.done():
                    task.cancel()
                    with suppress(asyncio.CancelledError):
                        await task
            await app.state.photos.close()
            await app.state.evolution.close()
            app.state.db.close()

    app = FastAPI(title="WhatsNexo", docs_url=None, redoc_url=None, openapi_url=None, root_path=settings.normalized_public_path, lifespan=lifespan)

    def check_origin(request: Request) -> None:
        origin = request.headers.get("origin")
        if not origin:
            return
        value = urlsplit(origin)
        expected = urlsplit(settings.public_origin) if settings.public_origin else urlsplit(str(request.url))
        expected_host = expected.netloc if settings.public_origin else request.headers.get("host", "")
        if value.scheme != expected.scheme or value.netloc.lower() != expected_host.lower() or value.path not in {"", "/"} or value.query or value.fragment:
            raise HTTPException(403, detail="origin_not_allowed")

    async def authenticate(username: str, password: str) -> str | None:
        async with app.state.auth_slots:
            return await asyncio.to_thread(app.state.users.authenticate, username, password)

    async def auth(request: Request, credentials: HTTPBasicCredentials | None = Depends(basic)) -> dict[str, Any]:
        if credentials:
            username = await authenticate(credentials.username, credentials.password)
            if username:
                result = {"mode": "basic", "username": username}
                request.state.auth = result
                return result
        token = request.cookies.get(COOKIE, "")
        session = await asyncio.to_thread(app.state.db.session, token) if token else None
        if session and app.state.users.contains(session["username"]):
            result = {**session, "mode": "cookie", "token": token}
            request.state.auth = result
            return result
        # No WWW-Authenticate: browsers use the explicit login screen.
        raise HTTPException(401, detail="authentication_required")

    async def mutation_auth(request: Request, user: dict[str, Any] = Depends(auth)) -> dict[str, Any]:
        check_origin(request)
        if request.headers.get("content-type", "").split(";")[0] != "application/json":
            raise HTTPException(415, detail="json_required")
        if user["mode"] == "cookie" and not equal_secret(request.headers.get("x-archive-csrf", ""), user["csrf"]):
            raise HTTPException(403, detail="csrf_required")
        return user

    @app.middleware("http")
    async def response_security(request: Request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; connect-src 'self'; script-src 'self'; base-uri 'self'; frame-ancestors 'none'"
        return response

    @app.exception_handler(EvolutionError)
    async def evolution_error(request: Request, error: EvolutionError):
        return JSONResponse(status_code=502, content={"detail": error.code, "upstream_status": error.status})

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, error: Exception):
        return JSONResponse(status_code=500, content={"detail": "archive_internal_error"})

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, error: RequestValidationError):
        # Pydantic normally echoes rejected input, including login passwords.
        return JSONResponse(status_code=422, content={"detail": "invalid_request", "fields": [list(item["loc"]) for item in error.errors()]})

    @app.get("/healthz")
    async def health():
        try:
            healthy = bool(await asyncio.to_thread(app.state.db.ping)) and not storage_state(settings)["write_blocked"]
        except Exception:
            healthy = False
        return JSONResponse(status_code=200 if healthy else 503, content={"service": "whatsapp-archive", "status": "ok" if healthy else "degraded"})

    @app.post("/api/login")
    async def login(body: LoginBody, request: Request, response: Response):
        check_origin(request)
        if request.headers.get("content-type", "").split(";")[0] != "application/json":
            raise HTTPException(415, detail="json_required")
        now = int(time.time())
        address = request.client.host if request.client else "unknown"
        failures = app.state.login_failures
        for key in list(failures):
            failures[key] = [when for when in failures[key] if when > now - 60]
            if not failures[key]:
                del failures[key]
        if len(failures.get(address, [])) >= 6:
            raise HTTPException(429, detail="login_rate_limited")
        username = await authenticate(body.username, body.password)
        if not username:
            if len(failures) > 5000:
                failures.clear()
            failures.setdefault(address, []).append(now)
            raise HTTPException(401, detail="invalid_credentials")
        failures.pop(address, None)
        token, csrf = secrets.token_urlsafe(48), secrets.token_urlsafe(32)
        expires = now + settings.session_ttl
        await asyncio.to_thread(app.state.db.add_session, token, csrf, expires, username)
        response.set_cookie(COOKIE, token, httponly=True, samesite="strict", secure=urlsplit(settings.public_origin).scheme == "https" or request.url.scheme == "https", max_age=settings.session_ttl, path=settings.cookie_path)
        return {"authenticated": True, "username": username, "csrf": csrf, "expires_at": expires}

    @app.get("/api/session")
    async def session(request: Request):
        current = await asyncio.to_thread(app.state.db.session, request.cookies.get(COOKIE, ""))
        return {"authenticated": True, **current} if current and app.state.users.contains(current["username"]) else {"authenticated": False}

    @app.post("/api/logout")
    async def logout(request: Request, response: Response, user: dict = Depends(mutation_auth)):
        await asyncio.to_thread(app.state.db.delete_session, request.cookies.get(COOKIE, ""))
        response.delete_cookie(COOKIE, path=settings.cookie_path, samesite="strict", httponly=True, secure=urlsplit(settings.public_origin).scheme == "https" or request.url.scheme == "https")
        return {"authenticated": False}

    def status_snapshot():
        db = app.state.db
        return {
            "instance": settings.instance, "capture_started": db.get_meta("capture_started"),
            "configured": True,
            "connection": db.get_meta("connection", {"instance": settings.instance, "state": "unknown"}),
            "counts": db.counts(), "coverage": db.coverage(),
            "sync": db.get_meta("sync", {"state": "idle", "processed": 0, "pages": 0, "current_page": 0, "incomplete": True, "error": None}),
            "history_signal": db.get_meta("history_signal"),
            "storage": storage_state(settings), "event_cursor": db.latest_event_id(),
        }

    @app.get("/api/status", dependencies=[Depends(auth)])
    async def status():
        return await asyncio.to_thread(status_snapshot)

    @app.get("/api/conversations", dependencies=[Depends(auth)])
    async def conversations(page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200), q: str | None = Query(None, max_length=200), unseen_only: bool = False, favorites_only: bool = False, label: str | None = Query(None, max_length=64), archived: Literal["active", "archived", "all"] = "active"):
        return await asyncio.to_thread(app.state.db.conversations, page, page_size, q, unseen_only, favorites_only, label, archived)

    @app.get("/api/conversations/photo", dependencies=[Depends(auth)])
    async def conversation_photo(chat: str = Query(..., max_length=2048)):
        if not valid_chat(chat):
            raise HTTPException(404, detail="profile_photo_unavailable")
        page = await asyncio.to_thread(app.state.db.messages, chat, None, 1, 1)
        if not page["total"]:
            raise HTTPException(404, detail="profile_photo_unavailable")
        image = await app.state.photos.get(chat)
        if image is None:
            raise HTTPException(404, detail="profile_photo_unavailable")
        try:
            content = await asyncio.to_thread(image.path.read_bytes)
        except FileNotFoundError:
            raise HTTPException(404, detail="profile_photo_unavailable") from None
        return Response(content, media_type=image.media_type)

    @app.get("/api/conversations/labels", dependencies=[Depends(auth)])
    async def conversation_labels():
        return {"items": await asyncio.to_thread(app.state.db.conversation_labels)}

    @app.post("/api/conversations/preferences", dependencies=[Depends(mutation_auth)])
    async def conversation_preferences(body: ConversationPreferencesBody):
        changes = body.model_dump(exclude_unset=True)
        changes.pop("chat")
        if not changes or any(value is None for value in changes.values()):
            raise HTTPException(422, detail="invalid_conversation_preferences")
        require_storage(settings)
        try:
            return await asyncio.to_thread(app.state.db.set_conversation_preferences, body.chat, **changes)
        except LookupError:
            raise HTTPException(404, detail="conversation_not_found") from None
        except ValueError:
            raise HTTPException(422, detail="invalid_conversation_preferences") from None

    @app.get("/api/search", dependencies=[Depends(auth)])
    async def search(q: str | None = Query(None, max_length=200), date_from: int | None = Query(None, ge=0, le=4102444800), date_to: int | None = Query(None, ge=0, le=4102444800), chat: str | None = Query(None, max_length=2048), type: Literal["text", "image", "video", "audio", "document", "sticker", "reaction", "button", "list", "poll", "location", "contact", "contacts", "system", "unknown"] | None = None, direction: Literal["in", "out"] | None = None, page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200)):
        if date_from is not None and date_to is not None and date_from > date_to:
            raise HTTPException(422, detail="invalid_date_range")
        return await asyncio.to_thread(app.state.db.search, q, date_from, date_to, chat, type, direction, page, page_size)

    @app.get("/api/messages", dependencies=[Depends(auth)])
    async def messages(chat: str | None = Query(None, max_length=2048), q: str | None = Query(None, max_length=200), page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200)):
        return await asyncio.to_thread(app.state.db.messages, chat, q, page, page_size)

    @app.post("/api/seen", dependencies=[Depends(mutation_auth)])
    async def seen(body: SeenBody):
        if body.ids and any(len(value) > 2048 for value in body.ids):
            raise HTTPException(422, detail="invalid_message_ids")
        return await asyncio.to_thread(app.state.db.mark_seen, body.chat, body.ids)

    @app.post("/api/instance/setup", dependencies=[Depends(mutation_auth)])
    async def setup():
        require_storage(settings)
        async with app.state.reconciler.start_lock:
            result = await app.state.evolution.setup()
            await asyncio.to_thread(app.state.db.set_meta, "setup", result)
            return result

    @app.get("/api/instance/connection", dependencies=[Depends(auth)])
    async def connection():
        try:
            result = await app.state.evolution.connection()
        except EvolutionError as error:
            result = {"instance": settings.instance, "state": "unknown", "error": error.code}
        result["updated_at"] = int(time.time())
        await asyncio.to_thread(app.state.db.set_meta, "connection", result, notify=True)
        return result

    @app.post("/api/instance/connect", dependencies=[Depends(mutation_auth)])
    async def connect():
        require_storage(settings)
        return await app.state.evolution.connect()

    @app.post("/api/history/sync", status_code=202, dependencies=[Depends(mutation_auth)])
    async def history_sync():
        started = await app.state.reconciler.start()
        return {"started": started, "sync": await asyncio.to_thread(app.state.db.get_meta, "sync")}

    @app.get("/api/events", dependencies=[Depends(auth)])
    async def events(request: Request, cursor: int = Query(0, ge=0)):
        last_id = request.headers.get("last-event-id")
        if last_id:
            if not last_id.isdigit():
                raise HTTPException(400, detail="invalid_event_cursor")
            cursor = int(last_id)
        latest = await asyncio.to_thread(app.state.db.latest_event_id)
        if cursor > latest:
            cursor = latest

        async def stream():
            nonlocal cursor
            heartbeat = time.monotonic()
            yield "retry: 3000\n\n"
            while not await request.is_disconnected():
                if request.state.auth["mode"] == "cookie" and not await asyncio.to_thread(app.state.db.session, request.state.auth["token"]):
                    break
                records = await asyncio.to_thread(app.state.db.events_since, cursor)
                for record in records:
                    cursor = record["id"]
                    yield "id: " + str(cursor) + "\nevent: archive\ndata: " + json.dumps(record["data"], ensure_ascii=False) + "\n\n"
                if time.monotonic() - heartbeat >= 15:
                    yield ": heartbeat\n\n"
                    heartbeat = time.monotonic()
                if not records:
                    await asyncio.sleep(0.5)

        return StreamingResponse(stream(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no", "Cache-Control": "no-store"})

    @app.post("/webhook/evolution")
    async def webhook(request: Request):
        if not equal_secret(request.headers.get("x-webhook-secret", ""), settings.webhook_secret):
            raise HTTPException(401, detail="webhook_authentication_required")
        require_storage(settings)
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > settings.maximum_body_bytes:
                raise HTTPException(413, detail="webhook_body_too_large")
        try:
            envelope = json.loads(body)
        except (ValueError, UnicodeError):
            raise HTTPException(400, detail="invalid_webhook_json") from None
        if not isinstance(envelope, dict) or not isinstance(envelope.get("event"), str) or "data" not in envelope:
            raise HTTPException(422, detail="invalid_webhook_envelope")
        if envelope.get("instance") != settings.instance:
            raise HTTPException(403, detail="instance_not_allowed")
        require_storage(settings)
        summary = await asyncio.to_thread(app.state.db.ingest, envelope)
        return {"ok": True, **summary}

    @app.get("/{path:path}")
    async def panel(path: str, request: Request):
        if path.startswith(("api/", "webhook/")):
            raise HTTPException(404, detail="not_found")
        root = settings.static_dir.resolve()
        target = (root / path).resolve()
        if not target.is_relative_to(root):
            raise HTTPException(404, detail="not_found")
        # Login UI and its public bundle contain no archive content or credentials.
        # All data access is authenticated by API/session, including SSE.
        if target.is_file():
            return FileResponse(target)
        index = root / "index.html"
        if index.is_file():
            return FileResponse(index)
        raise HTTPException(503, detail="panel_not_built")

    return app
