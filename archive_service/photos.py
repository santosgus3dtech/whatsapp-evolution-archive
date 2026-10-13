"""Private, bounded on-demand profile images. No upstream URLs are persisted."""
from __future__ import annotations

import asyncio
import hashlib
import ipaddress
import os
import re
import socket
import stat
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Awaitable, Callable
from urllib.parse import urlsplit

import httpx

from .evolution import EvolutionClient, valid_chat
from .settings import Settings
from .sync import require_storage


PHOTO_HOSTS = frozenset({"pps.whatsapp.net"})
MIME_EXTENSIONS = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
CACHE_NAME = re.compile(r"[a-f0-9]{64}\.(jpg|png|webp)")
TEMP_NAME = re.compile(r"[a-f0-9]{64}\.tmp-[a-f0-9]{32}")


@dataclass(frozen=True)
class CachedPhoto:
    path: Path
    media_type: str


def _public_ip(value: str) -> bool:
    address = ipaddress.ip_address(value)
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
        address = address.ipv4_mapped
    return address.is_global and not address.is_multicast


async def public_addresses(host: str) -> list[str]:
    async with asyncio.timeout(5):
        answers = await asyncio.get_running_loop().getaddrinfo(host, 443, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP)
    addresses = list(dict.fromkeys(answer[4][0] for answer in answers))
    if not addresses or any(not _public_ip(value) for value in addresses):
        raise ValueError("profile_host_unavailable")
    return addresses


def _raster_type(body: bytes) -> str | None:
    if body.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if body.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(body) >= 12 and body[:4] == b"RIFF" and body[8:12] == b"WEBP":
        return "image/webp"
    return None


class PhotoCache:
    def __init__(
        self, settings: Settings, evolution: EvolutionClient, *,
        ttl: int = 6 * 3600, negative_ttl: int = 300,
        max_files: int = 128, max_bytes: int = 32 * 1024**2,
        max_download: int = 1024**2,
        resolver: Callable[[str], Awaitable[list[str]]] = public_addresses,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        if min(ttl, negative_ttl, max_files, max_bytes, max_download) <= 0 or max_download > max_bytes:
            raise ValueError("invalid_photo_limits")
        self.settings, self.evolution = settings, evolution
        self.directory = settings.data_dir / "photos"
        self.ttl, self.negative_ttl = ttl, negative_ttl
        self.max_files, self.max_bytes, self.max_download = max_files, max_bytes, max_download
        self.resolver, self.transport = resolver, transport
        self.lock = asyncio.Lock()
        self.slots = asyncio.Semaphore(2)
        self.inflight: dict[str, asyncio.Task] = {}
        self.negative: OrderedDict[str, float] = OrderedDict()

    async def get(self, chat: str) -> CachedPhoto | None:
        if not valid_chat(chat):
            return None
        key = hashlib.sha256((self.settings.instance + "\0" + chat).encode()).hexdigest()
        async with self.lock:
            cached = await asyncio.to_thread(self._cached, key)
            if cached:
                return cached
            if self.negative.get(key, 0) > time.time():
                self.negative.move_to_end(key)
                return None
            self.negative.pop(key, None)
            task = self.inflight.get(key)
            if task is None:
                if len(self.inflight) >= self.max_files:
                    return None
                task = asyncio.create_task(self._fetch(chat, key), name="archive-profile-photo")
                self.inflight[key] = task
        # A disconnected browser must not cancel another request's shared fetch.
        return await asyncio.shield(task)

    async def close(self) -> None:
        tasks = list(self.inflight.values())
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    def _prepare_directory(self) -> None:
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        if self.directory.is_symlink() or not self.directory.is_dir():
            raise OSError("profile_cache_unavailable")
        self.directory.chmod(0o700)

    def _files(self):
        self._prepare_directory()
        files = []
        for path in self.directory.iterdir():
            if TEMP_NAME.fullmatch(path.name):
                info = path.lstat()
                if stat.S_ISREG(info.st_mode) and time.time() - info.st_mtime >= 60:
                    path.unlink()
                continue
            if not CACHE_NAME.fullmatch(path.name):
                continue
            info = path.lstat()
            if stat.S_ISREG(info.st_mode) and not path.is_symlink():
                files.append((path, info))
        return files

    def _cached(self, key: str) -> CachedPhoto | None:
        try:
            self._prepare_directory()
            for mime, extension in MIME_EXTENSIONS.items():
                path = self.directory / (key + extension)
                try:
                    info = path.lstat()
                except FileNotFoundError:
                    continue
                if not stat.S_ISREG(info.st_mode) or path.is_symlink():
                    continue
                if time.time() - info.st_mtime >= self.ttl or info.st_size > self.max_download:
                    path.unlink()
                    continue
                path.chmod(0o600)
                # Revalidate the signature before serving a file across restarts.
                with path.open("rb") as source:
                    if _raster_type(source.read(12)) != mime:
                        path.unlink()
                        continue
                return CachedPhoto(path, mime)
        except OSError:
            return None
        return None

    def _store(self, key: str, body: bytes, mime: str) -> CachedPhoto:
        require_storage(self.settings)
        files = sorted(self._files(), key=lambda item: item[1].st_mtime)
        now = time.time()
        survivors = []
        for path, info in files:
            if now - info.st_mtime >= self.ttl or path.stem == key:
                path.unlink()
            else:
                survivors.append((path, info))
        total = sum(info.st_size for _, info in survivors)
        while survivors and (len(survivors) >= self.max_files or total + len(body) > self.max_bytes):
            path, info = survivors.pop(0)
            path.unlink()
            total -= info.st_size
        path = self.directory / (key + MIME_EXTENSIONS[mime])
        temporary = self.directory / (key + ".tmp-" + uuid.uuid4().hex)
        try:
            descriptor = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(descriptor, "wb") as target:
                target.write(body)
                target.flush()
                os.fsync(target.fileno())
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
        return CachedPhoto(path, mime)

    async def _download(self, value: str) -> tuple[bytes, str] | None:
        parsed = urlsplit(value)
        if (len(value) > 8192 or any(ord(char) <= 32 for char in value) or
                parsed.scheme != "https" or parsed.hostname not in PHOTO_HOSTS or
                parsed.username or parsed.password or parsed.fragment or parsed.port not in {None, 443}):
            return None
        addresses = await self.resolver(parsed.hostname)
        if not addresses or any(not _public_ip(address) for address in addresses):
            return None
        # Pin the actual TCP destination to a validated public IP. Host and SNI
        # retain the official hostname for TLS verification; no second DNS lookup.
        url = httpx.URL(value).copy_with(host=addresses[0])
        async with httpx.AsyncClient(
            transport=self.transport, trust_env=False, follow_redirects=False,
            timeout=httpx.Timeout(10, connect=5),
        ) as client:
            async with client.stream("GET", url, headers={"Host": parsed.hostname, "Accept": "image/jpeg,image/png,image/webp", "Accept-Encoding": "identity"}, extensions={"sni_hostname": parsed.hostname}) as response:
                if response.status_code != 200 or response.headers.get("content-encoding", "identity").lower() != "identity":
                    return None
                mime = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
                if mime not in MIME_EXTENSIONS:
                    return None
                length = response.headers.get("content-length")
                if length and (not length.isdigit() or int(length) > self.max_download):
                    return None
                body = bytearray()
                async for chunk in response.aiter_bytes(chunk_size=64 * 1024):
                    body.extend(chunk)
                    if len(body) > self.max_download:
                        return None
                if _raster_type(body) != mime:
                    return None
                return bytes(body), mime

    async def _fetch(self, chat: str, key: str) -> CachedPhoto | None:
        photo = None
        try:
            async with self.slots, asyncio.timeout(30):
                value = await self.evolution.profile_url(chat)
                if value:
                    downloaded = await self._download(value)
                    if downloaded:
                        async with self.lock:
                            # Serialize eviction and rename. A task cancellation
                            # waits for this disk write before lifespan shutdown.
                            worker = asyncio.create_task(asyncio.to_thread(self._store, key, *downloaded))
                            try:
                                photo = await asyncio.shield(worker)
                            except asyncio.CancelledError:
                                await worker
                                raise
        except asyncio.CancelledError:
            raise
        except Exception:
            # Privacy denial, expiry, upstream 401, disk limits and network errors
            # all use the same neutral UI fallback. No URL/body/error is logged.
            pass
        finally:
            async with self.lock:
                self.inflight.pop(key, None)
                if photo is None:
                    self.negative[key] = time.time() + self.negative_ttl
                    self.negative.move_to_end(key)
                    while len(self.negative) > self.max_files:
                        self.negative.popitem(last=False)
        return photo
