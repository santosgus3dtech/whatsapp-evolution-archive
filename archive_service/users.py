"""Additional private accounts; existing environment credentials remain valid."""
from __future__ import annotations

import hashlib
import json
import secrets
from typing import Any

from .settings import Settings


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=16384, r=8, p=1, dklen=32)
    return "scrypt$16384$8$1$" + salt.hex() + "$" + digest.hex()


def parse_hash(value: Any) -> tuple[int, int, int, bytes, bytes]:
    try:
        algorithm, n, r, p, salt, digest = value.split("$")
        n, r, p = int(n), int(r), int(p)
        salt, digest = bytes.fromhex(salt), bytes.fromhex(digest)
        if algorithm != "scrypt" or n not in {16384, 32768, 65536} or not 1 <= r <= 8 or not 1 <= p <= 2 or len(salt) < 16 or len(salt) > 64 or len(digest) != 32:
            raise ValueError
        return n, r, p, salt, digest
    except (ValueError, TypeError, AttributeError):
        raise RuntimeError("Invalid password hash in ARCHIVE_USERS_FILE") from None


class UserDirectory:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.users: dict[str, tuple[int, int, int, bytes, bytes]] = {}
        if settings.users_file:
            try:
                if settings.users_file.stat().st_size > 1024 * 1024:
                    raise ValueError
                payload = json.loads(settings.users_file.read_text(encoding="utf-8"))
                entries = payload["users"]
                if not isinstance(entries, list) or len(entries) > 100:
                    raise ValueError
                for entry in entries:
                    username = entry["username"]
                    if not isinstance(username, str) or not 1 <= len(username) <= 128 or username != username.strip() or username == settings.username or username in self.users:
                        raise ValueError
                    self.users[username] = parse_hash(entry["password_hash"])
            except (OSError, ValueError, TypeError, KeyError):
                raise RuntimeError("Invalid ARCHIVE_USERS_FILE; existing account cannot be overridden") from None
        self.dummy = parse_hash(hash_password(secrets.token_urlsafe(32)))

    def contains(self, username: str) -> bool:
        return username == self.settings.username or username in self.users

    def authenticate(self, username: str, password: str) -> str | None:
        value = self.users.get(username, self.dummy)
        n, r, p, salt, digest = value
        try:
            candidate = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=n, r=r, p=p, dklen=32, maxmem=128 * 1024**2)
            additional = secrets.compare_digest(candidate, digest) and username in self.users
        except (ValueError, TypeError, MemoryError):
            additional = False
        legacy = secrets.compare_digest(username.encode("utf-8"), self.settings.username.encode("utf-8")) & secrets.compare_digest(password.encode("utf-8"), self.settings.password.encode("utf-8"))
        return username if additional or legacy else None
