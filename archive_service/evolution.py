from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote, urlsplit

import httpx

from .settings import Settings


EVENTS = ["MESSAGES_SET", "MESSAGES_UPSERT", "MESSAGES_UPDATE", "MESSAGES_EDITED", "MESSAGES_DELETE", "SEND_MESSAGE", "CONNECTION_UPDATE"]


def valid_chat(value: Any) -> bool:
    return isinstance(value, str) and len(value) <= 100 and re.fullmatch(r"[0-9]+(?:-[0-9]+)?@(s\.whatsapp\.net|g\.us|lid)", value) is not None


class EvolutionError(Exception):
    """Only a safe code and HTTP status may cross the API boundary."""

    def __init__(self, code: str, status: int | None = None):
        self.code = code
        self.status = status
        super().__init__(code)


class EvolutionClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = httpx.AsyncClient(
            base_url=settings.evolution_url.rstrip("/"),
            headers={"apikey": settings.evolution_key},
            timeout=httpx.Timeout(60, connect=10),
            follow_redirects=False,
        )

    @property
    def name(self) -> str:
        return quote(self.settings.instance, safe="")

    async def close(self) -> None:
        await self.client.aclose()

    async def request(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            response = await self.client.request(method, path, **kwargs)
            if response.status_code >= 400:
                raise EvolutionError("evolution_http_error", response.status_code)
            return response.json()
        except EvolutionError:
            raise
        except httpx.RequestError:
            raise EvolutionError("evolution_unreachable") from None
        except (ValueError, TypeError):
            raise EvolutionError("evolution_invalid_response") from None

    async def setup(self) -> dict[str, Any]:
        # 2.3.7 returns 404 for an instanceName filter when it does not exist.
        # Listing first keeps absence distinct from an upstream failure.
        response = await self.request("GET", "/instance/fetchInstances")
        if not isinstance(response, list):
            raise EvolutionError("evolution_invalid_instances")
        for record in response:
            if not isinstance(record, dict):
                continue
            nested = record.get("instance")
            nested = nested if isinstance(nested, dict) else {}
            if record.get("name") == self.settings.instance or nested.get("instanceName") == self.settings.instance:
                return {"created": False, "preserved": True, "instance": self.settings.instance, "webhook_configured": None}
        await self.request("POST", "/instance/create", json={
            "instanceName": self.settings.instance,
            "integration": "WHATSAPP-BAILEYS",
            "qrcode": False,
            "syncFullHistory": True,
            "groupsIgnore": False,
            "readMessages": False,
            "readStatus": False,
            "alwaysOnline": False,
            "webhook": {
                "enabled": True,
                "url": self.settings.internal_url + "/webhook/evolution",
                "byEvents": False,
                "base64": False,
                "headers": {"X-Webhook-Secret": self.settings.webhook_secret},
                "events": EVENTS,
            },
        })
        return {"created": True, "preserved": False, "instance": self.settings.instance, "webhook_configured": True}

    async def connection(self) -> dict[str, Any]:
        result = await self.request("GET", "/instance/connectionState/" + self.name)
        nested = result.get("instance", {}) if isinstance(result, dict) else {}
        state = nested.get("state") if isinstance(nested, dict) else None
        if not isinstance(state, str) or state not in {"open", "close", "connecting"}:
            state = "unknown"
        return {"instance": self.settings.instance, "state": state}

    async def connect(self) -> dict[str, Any]:
        result = await self.request("GET", "/instance/connect/" + self.name)
        if not isinstance(result, dict):
            raise EvolutionError("evolution_invalid_qr")
        normalized: dict[str, Any] = {}
        base64 = result.get("base64")
        # QR is the only base64 intentionally returned, and is never persisted.
        if isinstance(base64, str) and base64.startswith("data:image/") and len(base64) < 2 * 1024**2:
            normalized["base64"] = base64
        if isinstance(result.get("pairingCode"), str):
            normalized["pairingCode"] = result["pairingCode"][:100]
        if isinstance(result.get("count"), (int, float)):
            normalized["count"] = result["count"]
        if not normalized and isinstance(result.get("instance"), dict):
            normalized["state"] = result["instance"].get("state", "unknown")
        return normalized

    async def messages(self, page: int, size: int) -> dict[str, Any]:
        result = await self.request("POST", "/chat/findMessages/" + self.name, json={"where": {}, "page": page, "offset": size})
        result = result.get("messages") if isinstance(result, dict) else None
        if not isinstance(result, dict) or not isinstance(result.get("records"), list):
            raise EvolutionError("evolution_invalid_history")
        return result

    async def chats(self, page: int = 1, size: int = 100) -> list[dict[str, Any]]:
        """Read v2.3.7 chat summaries; discard URLs and lastMessage payloads.

        The release's Prisma Chat model and fetchChats SELECT do not expose an
        archived flag. Absence remains unknown, never inferred as unarchived.
        Source: evolution-api cd800f2976e1e5b682fbf86a01ee4d85ae61f370,
        src/api/services/channel.service.ts::fetchChats.
        """
        if isinstance(page, bool) or isinstance(size, bool) or not isinstance(page, int) or not isinstance(size, int) or page < 1 or not 1 <= size <= 200:
            raise EvolutionError("evolution_invalid_chat_query")
        result = await self.request("POST", "/chat/findChats/" + self.name, json={"where": {}, "take": size, "skip": (page - 1) * size})
        if not isinstance(result, list) or len(result) > size or any(not isinstance(row, dict) for row in result):
            raise EvolutionError("evolution_invalid_chats")
        summaries = []
        for row in result:
            if not valid_chat(row.get("remoteJid")):
                continue
            archived = row.get("archived")
            name = row.get("pushName")
            summaries.append({"chat": row["remoteJid"], "name": name[:256] if isinstance(name, str) else None, "archived_whatsapp": archived if isinstance(archived, bool) else None})
        return summaries

    async def profile_url(self, chat: str) -> str | None:
        """Return a private, short-lived URL to the backend photo cache only."""
        if not valid_chat(chat):
            raise EvolutionError("evolution_invalid_chat_query")
        result = await self.request("POST", "/chat/fetchProfilePictureUrl/" + self.name, json={"number": chat})
        if not isinstance(result, dict):
            raise EvolutionError("evolution_invalid_profile")
        value = result.get("profilePictureUrl")
        if value is None:
            return None
        if not isinstance(value, str) or len(value) > 8192:
            raise EvolutionError("evolution_invalid_profile")
        try:
            parsed = urlsplit(value)
            if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.fragment or parsed.port not in {None, 443}:
                raise ValueError
        except ValueError:
            raise EvolutionError("evolution_invalid_profile") from None
        return value
