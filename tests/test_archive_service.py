import asyncio
import json
import sqlite3
import time
from dataclasses import replace

import httpx
import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from archive_service.app import Reconciler, create_app
from archive_service.database import Database, timestamp_seconds
from archive_service.evolution import EvolutionClient, EvolutionError
from archive_service.settings import Settings
from archive_service.users import hash_password, UserDirectory


def message(message_id="m1", chat="5511000000000@s.whatsapp.net", timestamp=None, from_me=False, text="Synthetic message", **extra):
    return {"key": {"id": message_id, "remoteJid": chat, "fromMe": from_me}, "message": {"conversation": text}, "messageTimestamp": timestamp or int(time.time()) + 2, **extra}


def envelope(records, event="messages.upsert", **extra):
    return {"event": event, "instance": "test-instance", "data": records, **extra}


@pytest.fixture
def config(tmp_path):
    return Settings(data_dir=tmp_path / "data", username="test-user", password="synthetic-password", webhook_secret="synthetic-webhook-secret", evolution_url="http://evolution.test", evolution_key="synthetic-api-key", instance="test-instance", static_dir=tmp_path / "panel", minimum_free_bytes=0)


@pytest.fixture
def db(config):
    database = Database(config.data_dir / "archive.sqlite3", config.instance)
    yield database
    database.close()


class FakeEvolution:
    def __init__(self, pages=None, error=None):
        self.pages = pages or [{"records": [], "pages": 1, "currentPage": 1}]
        self.error = error
        self.calls = []

    async def setup(self):
        return {"created": True, "preserved": False, "instance": "test-instance", "webhook_configured": True}

    async def connection(self):
        if self.error:
            raise self.error
        return {"instance": "test-instance", "state": "close"}

    async def connect(self):
        return {"base64": "data:image/png;base64,U1lOVEhFVElD", "count": 1}

    async def messages(self, page, size):
        self.calls.append((page, size))
        if self.error:
            raise self.error
        return self.pages[min(page - 1, len(self.pages) - 1)]

    async def close(self):
        pass


def test_new_duplicate_history_own_and_notify_type(db):
    record = message()
    first = db.ingest(envelope(record))
    assert first["received_new"] == 1
    assert db.ingest(envelope(record))["duplicates"] == 1
    db.ingest(envelope(message("old", timestamp=db.get_meta("capture_started") - 10)))
    db.ingest(envelope(message("own", from_me=True)))
    db.ingest(envelope({"type": "append", "messages": [message("append")]}))
    db.ingest(envelope([message("set")], event="MESSAGES_SET", isLatest=True, progress=100))
    assert db.counts() == {"messages": 5, "conversations": 1, "unseen": 1, "received_new": 1}
    assert db.coverage()["complete"] is False
    assert db.get_meta("history_signal")["isLatest"] is True


def test_reconciliation_recovers_missed_new_but_never_relabels_duplicate(db):
    db.ingest(envelope([message("missing"), message("ancient", timestamp=db.get_meta("capture_started") - 100)]), source="reconcile")
    assert db.counts()["received_new"] == 1
    db.ingest(envelope(message("missing")))
    row = db.messages(None, None, 1, 50)["items"][0]
    assert row["source"] == "reconcile" and row["received_new"] is True
    db.mark_seen(None, None)
    db.ingest(envelope(message("missing")))
    assert db.counts()["unseen"] == 0
    # A historical sync event is never promoted by a later duplicate upsert.
    db.ingest(envelope(message("historical-set"), event="messages.set"))
    db.ingest(envelope(message("historical-set")))
    assert db.counts()["received_new"] == 1


def test_restart_capture_cursor_sessions_and_mark_seen_are_durable(config):
    first = Database(config.data_dir / "archive.sqlite3", config.instance)
    captured = first.get_meta("capture_started")
    first.ingest(envelope(message()))
    cursor = first.latest_event_id()
    first.mark_seen(None, None)
    first.add_session("opaque-synthetic-token", "synthetic-csrf", int(time.time()) + 60)
    first.close()
    second = Database(config.data_dir / "archive.sqlite3", config.instance)
    try:
        assert second.get_meta("capture_started") == captured
        assert second.counts()["unseen"] == 0
        assert second.events_since(cursor)[0]["data"]["kind"] == "seen"
        assert second.get_meta("seen_cursor") == cursor
        assert second.session("opaque-synthetic-token")["csrf"] == "synthetic-csrf"
        dump = "\n".join(second.conn.iterdump())
        assert "opaque-synthetic-token" not in dump
    finally:
        second.close()


def test_nested_media_only_keeps_caption_and_safe_metadata(db):
    record = message()
    record["message"] = {"ephemeralMessage": {"message": {"viewOnceMessage": {"message": {"imageMessage": {"caption": "Synthetic caption", "mimetype": "image/jpeg", "fileLength": 123, "url": "https://secret-media.test", "directPath": "private-path", "mediaKey": "secret-media-key", "base64": "SECRET_BASE64"}}}}}}
    db.ingest(envelope(record, apikey="SECRET_API", server_url="SECRET_SERVER", destination="SECRET_DESTINATION", headers={"Authorization": "SECRET_HEADER"}))
    row = db.messages(None, None, 1, 50)["items"][0]
    assert row["type"] == "image" and row["text"] == "Synthetic caption"
    assert row["metadata"] == {"has_media": True, "media_saved": False, "mimetype": "image/jpeg", "size": 123}
    dump = "\n".join(db.conn.iterdump())
    assert not any(secret in dump for secret in ["SECRET_API", "SECRET_SERVER", "SECRET_DESTINATION", "SECRET_HEADER", "SECRET_BASE64", "secret-media-key", "secret-media.test", "private-path"])


def test_timestamp_variants_and_invalid_payloads(db):
    assert timestamp_seconds(1700000000123) == 1700000000
    assert timestamp_seconds({"low": 1700000000, "high": 0}) == 1700000000
    assert timestamp_seconds({"seconds": "1700000000"}) == 1700000000
    assert timestamp_seconds(float("nan")) is None
    assert timestamp_seconds(True) is None
    assert db.ingest(envelope([{}, "not a record", {"key": {"id": "missing-chat"}}]))["invalid"] == 2
    assert db.counts()["messages"] == 0


def test_canonical_lid_name_search_pagination_and_local_unseen(db):
    first = message("canonical", chat="12345@lid", pushName="Synthetic Contact")
    first["key"]["remoteJidAlt"] = "5511999999999@s.whatsapp.net"
    db.ingest(envelope(first))
    db.ingest(envelope(message("canonical", chat="5511999999999@s.whatsapp.net", pushName="Synthetic Contact")))
    db.ingest(envelope(message("old-other", chat="5511888888888@s.whatsapp.net", timestamp=db.get_meta("capture_started") - 10)))
    assert db.counts()["messages"] == 2
    result = db.conversations(1, 1, "Synthetic Contact")
    assert result["total"] == 1 and result["items"][0]["chat"] == "5511999999999@s.whatsapp.net"
    assert db.conversations(1, 1, unseen_only=True)["total"] == 1
    assert db.conversations(2, 1)["total"] == 2
    assert len(db.conversations(2, 1)["items"]) == 1
    assert db.messages(None, "%", 1, 50)["total"] == 0
    assert db.mark_seen("5511999999999@s.whatsapp.net", ["canonical"])["marked"] == 1
    assert db.conversations(1, 50, unseen_only=True)["total"] == 0


def test_out_of_order_edit_delete_preserves_tombstone_and_restores_original(db):
    key = message()["key"]
    db.ingest(envelope({"key": key}, event="messages.delete"))
    assert db.counts()["received_new"] == 0
    db.ingest(envelope(message()))
    row = db.messages(None, None, 1, 50)["items"][0]
    assert row["deleted"] is True and row["received_new"] is True and row["from_me"] is False
    edited = {"key": key, "message": {"protocolMessage": {"key": key, "editedMessage": {"conversation": "Edited synthetic text"}}}}
    db.ingest(envelope(edited, event="messages.edited"))
    row = db.messages(None, None, 1, 50)["items"][0]
    assert row["edited"] is True and row["text"] == "Edited synthetic text"
    assert db.counts()["messages"] == 1


def test_webhook_auth_validation_and_no_secret_echo(config):
    app = create_app(config, FakeEvolution(), start_background=False)
    with TestClient(app) as client:
        assert client.get("/healthz").json() == {"service": "whatsapp-archive", "status": "ok"}
        assert client.get("/api/status").status_code == 401
        assert client.get("/api/events").status_code == 401
        assert client.post("/webhook/evolution", json=envelope(message())).status_code == 401
        headers = {"X-Webhook-Secret": config.webhook_secret}
        assert client.post("/webhook/evolution", json=envelope(message()), headers=headers).status_code == 200
        assert client.post("/webhook/evolution", content="{bad", headers=headers).status_code == 400
        assert client.post("/webhook/evolution", json={"event": "messages.upsert", "data": {}, "instance": "foreign"}, headers=headers).status_code == 403
        assert client.post("/webhook/evolution", json=[], headers=headers).status_code == 422
        assert "synthetic-password" not in client.post("/api/login", json={"username": "", "password": "synthetic-password"}).text
        assert client.get("/api/status", auth=(config.username, config.password)).json()["counts"]["messages"] == 1


def test_cookie_session_csrf_origin_logout(config):
    app = create_app(config, FakeEvolution(), start_background=False)
    with TestClient(app) as client:
        assert client.get("/api/session").json() == {"authenticated": False}
        blocked = client.post("/api/login", json={"username": config.username, "password": config.password}, headers={"Origin": "https://attacker.test"})
        assert blocked.status_code == 403
        result = client.post("/api/login", json={"username": config.username, "password": config.password})
        assert "HttpOnly" in result.headers["set-cookie"] and "SameSite=strict" in result.headers["set-cookie"]
        csrf = result.json()["csrf"]
        assert client.get("/api/session").json()["authenticated"] is True
        assert client.get("/api/status").status_code == 200
        assert client.post("/api/seen", json={}).status_code == 403
        assert client.post("/api/seen", json={}, headers={"X-Archive-CSRF": csrf, "Origin": "http://testserver"}).status_code == 200
        assert client.post("/api/seen", json={}, headers={"X-Archive-CSRF": csrf, "Origin": "https://attacker.test"}).status_code == 403
        assert client.post("/api/logout", json={}, headers={"X-Archive-CSRF": csrf}).json() == {"authenticated": False}
        assert client.get("/api/status").status_code == 401


def test_disk_low_does_not_ack_or_write(config, monkeypatch):
    from archive_service import app as app_module
    config = replace(config, minimum_free_bytes=2 * 1024**3)
    app = create_app(config, FakeEvolution(), start_background=False)
    with TestClient(app) as client:
        monkeypatch.setattr(app_module, "storage_state", lambda _: {"free_bytes": 1, "minimum_free_bytes": 2 * 1024**3, "write_blocked": True})
        result = client.post("/webhook/evolution", json=envelope(message()), headers={"X-Webhook-Secret": config.webhook_secret})
        assert result.status_code == 503
        assert app.state.db.counts()["messages"] == 0
        assert client.get("/healthz").status_code == 503
        assert client.get("/api/status", auth=(config.username, config.password)).json()["storage"]["write_blocked"] is True


def test_reconciliation_pagination_limits_and_lock(db, config):
    async def run():
        pages = [{"records": [message("page1")], "pages": 2, "currentPage": 1}, {"records": [message("page2")], "pages": 2, "currentPage": 2}]
        fake = FakeEvolution(pages)
        reconciler = Reconciler(db, fake, config)
        assert await reconciler.start() is True
        assert await reconciler.start() is False
        await reconciler.task
        assert fake.calls == [(1, 100), (2, 100)]
        assert db.counts()["messages"] == 2
        assert db.get_meta("sync")["incomplete"] is False
        limited = Reconciler(db, FakeEvolution(pages), replace(config, sync_max_pages=1))
        await limited.start()
        await limited.task
        assert db.get_meta("sync")["error"] == "history_page_limit"
        assert db.get_meta("sync")["incomplete"] is True
    asyncio.run(run())


def test_evolution_contract_and_preserve_existing(config):
    calls = []

    def handler(request):
        calls.append(request)
        if request.url.path.endswith("fetchInstances"):
            if request.url.params.get("instanceName"):
                return httpx.Response(404, json={"error": "Not Found"})
            return httpx.Response(200, json=[])
        if request.url.path.endswith("create"):
            return httpx.Response(201, json={"apikey": "MUST_NOT_RETURN"})
        return httpx.Response(200, json={"messages": {"total": 0, "pages": 0, "currentPage": 1, "records": []}})

    async def run():
        client = EvolutionClient(config)
        await client.client.aclose()
        client.client = httpx.AsyncClient(base_url=config.evolution_url, transport=httpx.MockTransport(handler), headers={"apikey": config.evolution_key})
        result = await client.setup()
        assert result["created"] is True and "apikey" not in result
        assert not calls[0].url.query
        payload = json.loads(calls[1].content)
        assert payload["qrcode"] is False and payload["syncFullHistory"] is True
        assert payload["readMessages"] is False and payload["readStatus"] is False
        assert payload["webhook"]["base64"] is False
        assert payload["webhook"]["headers"]["X-Webhook-Secret"] == config.webhook_secret
        await client.messages(1, 100)
        assert json.loads(calls[-1].content) == {"where": {}, "page": 1, "offset": 100}
        await client.close()
        preserved = EvolutionClient(config)
        await preserved.client.aclose()
        preserved_calls = []
        def existing_handler(request):
            preserved_calls.append(request)
            assert request.method == "GET" and not request.url.query
            return httpx.Response(200, json=[{"name": "another-instance"}, {"name": config.instance}])
        preserved.client = httpx.AsyncClient(base_url=config.evolution_url, transport=httpx.MockTransport(existing_handler))
        assert (await preserved.setup())["preserved"] is True
        assert len(preserved_calls) == 1
        await preserved.close()
    asyncio.run(run())


def test_sse_durable_replay_excludes_raw_payload(config):
    app = create_app(config, FakeEvolution(), start_background=False)
    with TestClient(app):
        app.state.db.ingest(envelope(message("one")))
        first_cursor = app.state.db.latest_event_id()
        app.state.db.ingest(envelope(message("two"), apikey="NEVER_IN_SSE"))
        route = next(route for route in app.routes if getattr(route, "path", None) == "/api/events")

        async def run():
            async def receive():
                return {"type": "http.request", "body": b"", "more_body": False}
            request = Request({"type": "http", "method": "GET", "path": "/api/events", "headers": [(b"last-event-id", str(first_cursor).encode())], "query_string": b"", "scheme": "http", "server": ("testserver", 80), "client": ("test", 1)}, receive=receive)
            request.state.auth = {"mode": "basic"}
            response = await route.endpoint(request, cursor=0)
            stream = response.body_iterator
            assert await anext(stream) == "retry: 3000\n\n"
            event = await anext(stream)
            assert "message_id\": \"two" in event and "NEVER_IN_SSE" not in event
            assert "id: " + str(first_cursor + 1) in event
            await stream.aclose()
        asyncio.run(run())


def test_settings_refuse_empty_secrets(config):
    with pytest.raises(RuntimeError, match="WEBHOOK_SECRET"):
        replace(config, webhook_secret="").validate()


def test_evolution_237_direct_update_edit_and_delete_formats(db):
    # Source: release 2.3.7 whatsapp.baileys.service.ts emit sites:
    # messages.update sends keyId/remoteJid/status; edited sends ProtocolMessage;
    # delete sends a WAMessageKey directly or a complete DB message with key.
    record = message()
    db.ingest(envelope(record))
    direct_update = {"keyId": "m1", "remoteJid": record["key"]["remoteJid"], "fromMe": False, "status": "READ", "messageId": "different-upstream-db-uuid"}
    db.ingest(envelope(direct_update, event="MESSAGES_UPDATE"))
    row = db.messages(None, None, 1, 50)["items"][0]
    assert row["metadata"]["whatsapp_status"] == "READ"
    assert row["seen"] is False and db.counts()["messages"] == 1
    direct_edit = {"key": record["key"], "editedMessage": {"conversation": "Edited via protocol"}, "type": 14, "timestampMs": int(time.time()) * 1000}
    db.ingest(envelope(direct_edit, event="MESSAGES_EDITED"))
    row = db.messages(None, None, 1, 50)["items"][0]
    assert row["text"] == "Edited via protocol" and row["edited"] is True
    db.ingest(envelope(record), source="reconcile")
    assert db.messages(None, None, 1, 50)["items"][0]["text"] == "Edited via protocol"
    db.ingest(envelope({**record["key"], "status": "DELETED"}, event="MESSAGES_DELETE"))
    assert db.messages(None, None, 1, 50)["items"][0]["deleted"] is True
    assert db.counts()["messages"] == 1


def test_reconcile_errors_are_persistent_safe_and_restartable(db, config):
    async def run():
        broken = Reconciler(db, FakeEvolution(error=EvolutionError("evolution_http_error", 401)), config)
        await broken.start()
        await broken.task
        assert db.get_meta("sync")["state"] == "error"
        assert db.get_meta("sync")["upstream_status"] == 401
        malformed = Reconciler(db, FakeEvolution([{"records": [{}], "pages": 1, "currentPage": 1}]), config)
        await malformed.start()
        await malformed.task
        assert db.get_meta("sync")["error"] == "history_invalid_records"
        repair = Reconciler(db, FakeEvolution(), config)
        await repair.start()
        await repair.task
        assert db.get_meta("sync")["state"] == "complete"
        assert db.get_meta("sync")["error"] is None
    asyncio.run(run())


def test_public_prefix_tls_cookie_csrf_assets_and_session_owner(config):
    users_file = config.data_dir.parent / "synthetic-users.json"
    users_file.write_text(json.dumps({"users": [{"username": "synthetic-second-user", "password_hash": hash_password("synthetic-second-password")}]}), encoding="utf-8")
    config.static_dir.mkdir()
    (config.static_dir / "index.html").write_text("Synthetic login bundle", encoding="utf-8")
    config = replace(config, users_file=users_file, public_origin="https://archive.example.test", public_path="/whatsapp/")
    app = create_app(config, FakeEvolution(), start_background=False)
    with TestClient(app, base_url="https://archive.example.test") as client:
        assert client.get("/whatsapp/").text == "Synthetic login bundle"
        assert client.get("/whatsapp/api/status").status_code == 401
        result = client.post("/whatsapp/api/login", json={"username": "synthetic-second-user", "password": "synthetic-second-password"}, headers={"Origin": "https://archive.example.test"})
        assert result.status_code == 200
        cookie = result.headers["set-cookie"]
        assert "whatsapp_archive_session=" in cookie and "Path=/whatsapp/" in cookie
        assert "Secure" in cookie and "HttpOnly" in cookie and "SameSite=strict" in cookie
        assert result.json()["username"] == "synthetic-second-user"
        assert client.get("/whatsapp/api/session").json()["username"] == "synthetic-second-user"
        csrf = result.json()["csrf"]
        assert client.post("/whatsapp/api/seen", json={}, headers={"Origin": "https://archive.example.test", "X-Archive-CSRF": csrf}).status_code == 200
        assert client.post("/whatsapp/api/seen", json={}, headers={"Origin": "https://other.test", "X-Archive-CSRF": csrf}).status_code == 403
        assert client.post("/whatsapp/api/logout", json={}, headers={"Origin": "https://archive.example.test", "X-Archive-CSRF": csrf}).status_code == 200
        assert client.get("/whatsapp/api/status").status_code == 401
        legacy = client.post("/whatsapp/api/login", json={"username": config.username, "password": config.password}, headers={"Origin": "https://archive.example.test"})
        assert legacy.status_code == 200 and legacy.json()["username"] == config.username
        # Public origin drives TLS cookie/CSRF even when the proxy talks HTTP internally.
        internal = client.post("http://archive.internal/whatsapp/api/login", json={"username": config.username, "password": config.password}, headers={"Origin": "https://archive.example.test"})
        assert internal.status_code == 200 and "Secure" in internal.headers["set-cookie"]
        redirect = client.get("http://archive.internal/api/status/", follow_redirects=False)
        assert redirect.status_code == 404 and "location" not in redirect.headers


def test_old_session_migration_keeps_legacy_owner(config):
    import hashlib
    config.data_dir.mkdir()
    path = config.data_dir / "archive.sqlite3"
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE sessions(token_hash TEXT PRIMARY KEY,csrf TEXT NOT NULL,expires_at INTEGER NOT NULL)")
    conn.execute("INSERT INTO sessions VALUES(?,?,?)", (hashlib.sha256(b"synthetic-existing-session").hexdigest(), "existing-synthetic-csrf", int(time.time()) + 60))
    conn.commit()
    conn.close()
    database = Database(path, config.instance, config.username)
    try:
        existing = database.session("synthetic-existing-session")
        assert existing["username"] == config.username and existing["csrf"] == "existing-synthetic-csrf"
    finally:
        database.close()


def test_extra_users_cannot_override_existing_account_and_bad_prefixes_fail(config):
    users_file = config.data_dir.parent / "synthetic-users.json"
    users_file.write_text(json.dumps({"users": [{"username": config.username, "password_hash": hash_password("synthetic-other-password")}]}), encoding="utf-8")
    with pytest.raises(RuntimeError, match="cannot be overridden"):
        UserDirectory(replace(config, users_file=users_file))
    for path in ("/whatsapp/../admin", "/whatsapp//api", "/whatsapp%2Fadmin", "https://other.test"):
        with pytest.raises(RuntimeError, match="ARCHIVE_PUBLIC_PATH"):
            replace(config, public_path=path).validate()
    with pytest.raises(RuntimeError, match="ARCHIVE_PUBLIC_ORIGIN"):
        replace(config, public_origin="http://archive.example.test").validate()
    with pytest.raises(RuntimeError, match="ARCHIVE_PUBLIC_ORIGIN"):
        replace(config, public_origin="https://archive.example.test/whatsapp").validate()


def test_lan_http_cookie_session_owner_and_csrf_logout(config):
    users_file = config.data_dir.parent / "synthetic-lan-users.json"
    users_file.write_text(json.dumps({"users": [{"username": "synthetic-lan-user", "password_hash": hash_password("synthetic-lan-password")}]}), encoding="utf-8")
    origin = "http://192.168.10.20:8097"
    config = replace(config, users_file=users_file, public_origin=origin, public_path="/")
    app = create_app(config, FakeEvolution(), start_background=False)
    with TestClient(app, base_url=origin) as client:
        result = client.post("/api/login", json={"username": "synthetic-lan-user", "password": "synthetic-lan-password"}, headers={"Origin": origin})
        assert result.status_code == 200
        cookie = result.headers["set-cookie"]
        assert "Secure" not in cookie and "Path=/" in cookie and "HttpOnly" in cookie and "SameSite=strict" in cookie
        assert client.get("/api/session").json()["username"] == "synthetic-lan-user"
        assert client.get("/api/status").status_code == 200
        csrf = result.json()["csrf"]
        assert client.post("/api/logout", json={}, headers={"X-Archive-CSRF": csrf, "Origin": "https://external.test"}).status_code == 403
        assert client.post("/api/logout", json={}).status_code == 403
        logout = client.post("/api/logout", json={}, headers={"X-Archive-CSRF": csrf, "Origin": origin})
        assert logout.status_code == 200 and "Secure" not in logout.headers["set-cookie"]
        assert client.get("/api/session").json() == {"authenticated": False}
        assert client.get("/api/status").status_code == 401
        legacy = client.post("/api/login", json={"username": config.username, "password": config.password}, headers={"Origin": origin})
        assert legacy.status_code == 200 and legacy.json()["username"] == config.username


def test_http_origin_only_allows_exact_rfc1918_ranges(config):
    for origin in ("http://10.1.2.3:8097", "http://172.16.1.2", "http://172.31.255.254", "http://192.168.10.20:8097"):
        replace(config, public_origin=origin).validate()
    for origin in ("http://archive.example.test", "http://8.8.8.8", "http://127.0.0.1", "http://169.254.1.1", "http://172.15.255.255", "http://172.32.0.1", "http://192.0.0.1", "http://[fd00::1]", "http://user:password@192.168.10.20", "http://192.168.10.20/whatsapp"):
        with pytest.raises(RuntimeError, match="ARCHIVE_PUBLIC_ORIGIN"):
            replace(config, public_origin=origin).validate()
