from __future__ import annotations

import os
import ipaddress
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    username: str
    password: str
    webhook_secret: str
    evolution_url: str
    evolution_key: str
    instance: str
    internal_url: str = "http://archive:8000"
    static_dir: Path = Path("apps/panel/dist")
    sync_interval: int = 300
    sync_max_pages: int = 1000
    sync_page_size: int = 100
    minimum_free_bytes: int = 2 * 1024**3
    session_ttl: int = 12 * 3600
    maximum_body_bytes: int = 16 * 1024**2
    users_file: Path | None = None
    public_origin: str = ""
    public_path: str = ""

    @classmethod
    def from_env(cls) -> "Settings":
        settings = cls(
            data_dir=Path(os.getenv("ARCHIVE_DATA_DIR", "./data")),
            username=os.getenv("ARCHIVE_USERNAME", ""),
            password=os.getenv("ARCHIVE_PASSWORD", ""),
            webhook_secret=os.getenv("WEBHOOK_SECRET", ""),
            evolution_url=os.getenv("EVOLUTION_API_URL", "http://evolution:8080").rstrip("/"),
            evolution_key=os.getenv("EVOLUTION_API_KEY", ""),
            instance=os.getenv("EVOLUTION_INSTANCE", "whatsapp-personal"),
            internal_url=os.getenv("ARCHIVE_INTERNAL_URL", "http://archive:8000").rstrip("/"),
            static_dir=Path(os.getenv("ARCHIVE_STATIC_DIR", "apps/panel/dist")),
            sync_interval=int(os.getenv("ARCHIVE_SYNC_INTERVAL_SECONDS", "300")),
            sync_max_pages=int(os.getenv("ARCHIVE_SYNC_MAX_PAGES", "1000")),
            sync_page_size=int(os.getenv("ARCHIVE_SYNC_PAGE_SIZE", "100")),
            users_file=Path(os.environ["ARCHIVE_USERS_FILE"]) if os.getenv("ARCHIVE_USERS_FILE") else None,
            public_origin=os.getenv("ARCHIVE_PUBLIC_ORIGIN", "").rstrip("/"),
            public_path=os.getenv("ARCHIVE_PUBLIC_PATH", "").rstrip("/"),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        missing = [name for name, value in {
            "ARCHIVE_USERNAME": self.username,
            "ARCHIVE_PASSWORD": self.password,
            "WEBHOOK_SECRET": self.webhook_secret,
            "EVOLUTION_API_KEY": self.evolution_key,
            "EVOLUTION_INSTANCE": self.instance,
        }.items() if not value.strip()]
        if missing:
            raise RuntimeError("Required configuration is empty: " + ", ".join(missing))
        if not all(c.isalnum() or c in "_-" for c in self.instance):
            raise RuntimeError("EVOLUTION_INSTANCE must use letters, numbers, underscore or hyphen")
        for name, value in (("EVOLUTION_API_URL", self.evolution_url), ("ARCHIVE_INTERNAL_URL", self.internal_url)):
            url = urlsplit(value)
            if url.scheme not in {"http", "https"} or not url.netloc or url.username or url.password or url.query or url.fragment:
                raise RuntimeError(name + " must be an HTTP(S) URL without credentials, query or fragment")
        if self.sync_interval < 1 or not 1 <= self.sync_max_pages <= 10000 or not 1 <= self.sync_page_size <= 1000:
            raise RuntimeError("Invalid history reconciliation limits")
        if self.minimum_free_bytes < 0 or self.session_ttl < 60:
            raise RuntimeError("Invalid archive storage/session limits")
        if self.normalized_public_path:
            import re
            if not re.fullmatch(r"(?:/[A-Za-z0-9_-]+)+", self.normalized_public_path):
                raise RuntimeError("ARCHIVE_PUBLIC_PATH must be a URL path without traversal or query")
        if self.public_origin:
            origin = urlsplit(self.public_origin)
            private_http = False
            if origin.scheme == "http" and origin.hostname:
                try:
                    address = ipaddress.ip_address(origin.hostname)
                    private_http = any(address in ipaddress.ip_network(network) for network in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"))
                except ValueError:
                    pass
            if (origin.scheme != "https" and not private_http) or not origin.hostname or origin.username or origin.password or origin.path not in {"", "/"} or origin.query or origin.fragment:
                raise RuntimeError("ARCHIVE_PUBLIC_ORIGIN requires HTTPS, or HTTP on an RFC1918 IP, without path or credentials")

    @property
    def normalized_public_path(self) -> str:
        return self.public_path.rstrip("/")

    @property
    def cookie_path(self) -> str:
        return self.normalized_public_path + "/"
