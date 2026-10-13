import asyncio
import hashlib
import os
import time

import httpx
import pytest

from archive_service.evolution import EvolutionClient, EvolutionError
from archive_service.photos import PhotoCache
from archive_service.settings import Settings


CHAT = "123456@s.whatsapp.net"
IMAGE = b"\x89PNG\r\n\x1a\n" + b"synthetic raster bytes"


def config(path):
    return Settings(data_dir=path, username="synthetic", password="synthetic-password", webhook_secret="synthetic-secret", evolution_url="http://evolution.test", evolution_key="synthetic-key", instance="synthetic", minimum_free_bytes=0)


class Profile:
    def __init__(self, value="https://pps.whatsapp.net/synthetic.png?token=NEVER_PERSISTED", error=None):
        self.value, self.error, self.calls = value, error, []

    async def profile_url(self, chat):
        self.calls.append(chat)
        if self.error:
            raise self.error
        return self.value


async def resolver(host):
    assert host == "pps.whatsapp.net"
    return ["8.8.8.8"]  # Synthetic destination; MockTransport never connects.


def test_private_cache_is_hashed_bounded_and_never_receives_api_key(tmp_path):
    async def scenario():
        requests = []
        def handler(request):
            requests.append(request)
            assert request.url.host == "8.8.8.8"
            assert request.headers["host"] == "pps.whatsapp.net"
            assert request.extensions["sni_hostname"] == "pps.whatsapp.net"
            assert "apikey" not in request.headers and "authorization" not in request.headers
            return httpx.Response(200, content=IMAGE, headers={"content-type": "image/png"})
        api = Profile()
        cache = PhotoCache(config(tmp_path), api, max_files=1, max_bytes=100, max_download=100, resolver=resolver, transport=httpx.MockTransport(handler))
        first = await cache.get(CHAT)
        assert first.path.read_bytes() == IMAGE and first.media_type == "image/png"
        assert first.path.name == hashlib.sha256(("synthetic\0" + CHAT).encode()).hexdigest() + ".png"
        assert (await cache.get(CHAT)).path == first.path and len(api.calls) == 1
        second = await cache.get("987654@s.whatsapp.net")
        assert second is not None and not first.path.exists()
        assert len(list(cache.directory.glob("*.png"))) == 1
        assert all(CHAT not in path.name and "token" not in path.name for path in cache.directory.iterdir())
        if os.name != "nt":
            assert cache.directory.stat().st_mode & 0o777 == 0o700
            assert second.path.stat().st_mode & 0o777 == 0o600
        await cache.close()
    asyncio.run(scenario())


@pytest.mark.parametrize("url", [
    "http://pps.whatsapp.net/synthetic.png", "https://pps.whatsapp.net:8443/x",
    "https://user:password@pps.whatsapp.net/x", "https://pps.whatsapp.net.evil.test/x",
    "https://127.0.0.1/x", "https://pps.whatsapp.net/x#fragment",
    "https://pps.whatsapp.net/x\nheader", "https://evil.test/x",
])
def test_url_allowlist_rejects_before_dns_or_download(tmp_path, url):
    async def scenario():
        async def forbidden(_):
            pytest.fail("Rejected URL reached DNS")
        cache = PhotoCache(config(tmp_path), Profile(url), resolver=forbidden)
        assert await cache.get(CHAT) is None
        await cache.close()
    asyncio.run(scenario())


@pytest.mark.parametrize("addresses", [["127.0.0.1"], ["10.1.2.3"], ["169.254.169.254"], ["::1"], ["::ffff:192.168.1.2"], ["8.8.8.8", "172.16.1.2"], []])
def test_all_dns_results_must_be_public(tmp_path, addresses):
    async def scenario():
        async def private_resolver(_):
            return addresses
        def forbidden(_):
            pytest.fail("Private DNS result reached download")
        cache = PhotoCache(config(tmp_path), Profile(), resolver=private_resolver, transport=httpx.MockTransport(forbidden))
        assert await cache.get(CHAT) is None
        await cache.close()
    asyncio.run(scenario())


@pytest.mark.parametrize("status,headers,body", [
    (302, {"location": "http://127.0.0.1/private"}, b""),
    (401, {"content-type": "image/png"}, IMAGE),
    (200, {"content-type": "image/svg+xml"}, b"<svg>private</svg>"),
    (200, {"content-type": "image/png"}, b"<svg>fake png</svg>"),
    (200, {"content-type": "image/png", "content-length": "1000"}, IMAGE),
    (200, {"content-type": "image/png"}, IMAGE * 8),
    (200, {"content-type": "image/png", "content-encoding": "gzip"}, b"invalid"),
])
def test_bad_response_uses_negative_cache_and_neutral_fallback(tmp_path, status, headers, body):
    async def scenario():
        api = Profile()
        calls = []
        def handler(request):
            calls.append(request)
            return httpx.Response(status, content=body, headers=headers)
        cache = PhotoCache(config(tmp_path), api, max_download=100, resolver=resolver, transport=httpx.MockTransport(handler))
        assert await cache.get(CHAT) is None
        assert await cache.get(CHAT) is None
        assert len(api.calls) == len(calls) == 1
        assert not list(cache.directory.glob("*.png"))
        await cache.close()
    asyncio.run(scenario())


def test_ttl_expiry_restart_and_coalesced_requests(tmp_path):
    async def scenario():
        api = Profile()
        def handler(_):
            return httpx.Response(200, content=IMAGE, headers={"content-type": "image/png"})
        cache = PhotoCache(config(tmp_path), api, ttl=10, resolver=resolver, transport=httpx.MockTransport(handler))
        photos = await asyncio.gather(*(cache.get(CHAT) for _ in range(5)))
        assert len(api.calls) == 1 and all(photo.path == photos[0].path for photo in photos)
        restored = PhotoCache(config(tmp_path), api, ttl=10, resolver=resolver, transport=httpx.MockTransport(handler))
        assert await restored.get(CHAT) is not None and len(api.calls) == 1
        os.utime(photos[0].path, (time.time() - 20, time.time() - 20))
        assert await restored.get(CHAT) is not None and len(api.calls) == 2
        await cache.close()
        await restored.close()
    asyncio.run(scenario())


def test_upstream_denial_and_invalid_chat_never_persist_or_download(tmp_path):
    async def scenario():
        api = Profile(error=EvolutionError("evolution_http_error", 401))
        cache = PhotoCache(config(tmp_path), api, resolver=resolver)
        assert await cache.get("../unauthorized") is None and not api.calls
        assert await cache.get(CHAT) is None and await cache.get(CHAT) is None
        assert api.calls == [CHAT] and not list(cache.directory.iterdir())
        await cache.close()
    asyncio.run(scenario())


def test_evolution_read_methods_discard_url_payload_and_keep_archive_unknown(tmp_path):
    async def scenario():
        client = EvolutionClient(config(tmp_path))
        await client.client.aclose()
        calls = []
        def handler(request):
            calls.append(request)
            if "findChats" in request.url.path:
                return httpx.Response(200, json=[{"remoteJid": CHAT, "pushName": "Synthetic", "profilePicUrl": "NEVER_RETURN", "lastMessage": {"secret": "NEVER_RETURN"}, "unreadCount": 7}])
            return httpx.Response(200, json={"profilePictureUrl": None})
        client.client = httpx.AsyncClient(base_url=client.settings.evolution_url, transport=httpx.MockTransport(handler))
        chats = await client.chats(2, 50)
        assert chats == [{"chat": CHAT, "name": "Synthetic", "archived_whatsapp": None}]
        assert "NEVER_RETURN" not in str(chats)
        assert await client.profile_url(CHAT) is None
        assert all(request.method == "POST" for request in calls)
        assert all("archiveChat" not in request.url.path for request in calls)
        await client.close()
    asyncio.run(scenario())
