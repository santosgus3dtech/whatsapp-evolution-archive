import base64

from fastapi.testclient import TestClient

from archive_service.app import create_app
from archive_service.photos import CachedPhoto
from archive_service.settings import Settings


PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+j1ioAAAAASUVORK5CYII=")
CHAT = "5511000000000@s.whatsapp.net"


class FakeEvolution:
    async def close(self):
        pass


class FakePhotos:
    def __init__(self, photo):
        self.photo = photo
        self.calls = []
        self.closed = False

    async def get(self, chat):
        self.calls.append(chat)
        return self.photo

    async def close(self):
        self.closed = True


def test_profile_route_is_private_known_chat_only_and_handles_eviction(tmp_path):
    settings = Settings(data_dir=tmp_path / "data", username="qa", password="synthetic-password", webhook_secret="qa-secret", evolution_url="http://evolution.test", evolution_key="qa-key", instance="qa", minimum_free_bytes=0)
    image = tmp_path / "profile.png"
    image.write_bytes(PNG)
    photos = FakePhotos(CachedPhoto(image, "image/png"))
    with TestClient(create_app(settings, FakeEvolution(), False, photos)) as client:
        db = client.app.state.db
        db.ingest({"event": "messages.set", "instance": "qa", "data": [{"key": {"id": "synthetic", "remoteJid": CHAT, "fromMe": False}, "messageTimestamp": 1700000000, "message": {"conversation": "Synthetic"}}]})
        route = "/api/conversations/photo"
        assert client.get(route, params={"chat": CHAT}).status_code == 401
        assert photos.calls == []
        login = client.post("/api/login", json={"username": "qa", "password": "synthetic-password"})
        assert login.status_code == 200
        for chat in ("https://private.invalid/photo", "5511000000999@s.whatsapp.net"):
            assert client.get(route, params={"chat": chat}).status_code == 404
        assert photos.calls == []
        response = client.get(route, params={"chat": CHAT})
        assert response.status_code == 200 and response.content == PNG
        assert response.headers["content-type"] == "image/png"
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["x-content-type-options"] == "nosniff"
        assert "http" not in response.headers.get("location", "")
        photos.photo = None
        assert client.get(route, params={"chat": CHAT}).status_code == 404
        photos.photo = CachedPhoto(image, "image/png")
        image.unlink()
        response = client.get(route, params={"chat": CHAT})
        assert response.status_code == 404 and response.json()["detail"] == "profile_photo_unavailable"
        db.ping = lambda: False
        assert client.get("/healthz").status_code == 503
    assert photos.closed
