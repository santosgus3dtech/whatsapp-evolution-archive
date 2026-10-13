"""Synthetic archive search/local organization tests; never use operational data."""
import json
import sqlite3
import time
import threading

import pytest
from fastapi.testclient import TestClient

from archive_service.app import create_app
from archive_service.database import Database
from archive_service.settings import Settings


CHAT_A = "5511000000001@s.whatsapp.net"
CHAT_B = "5511000000002@s.whatsapp.net"
CHAT_C = "5511000000003@s.whatsapp.net"


class NoNetwork:
    async def close(self):
        pass


@pytest.fixture
def config(tmp_path):
    return Settings(data_dir=tmp_path / "data", username="synthetic-admin", password="synthetic-password", webhook_secret="synthetic-webhook", evolution_url="http://synthetic.test", evolution_key="synthetic-api-key", instance="synthetic-instance", static_dir=tmp_path / "panel", minimum_free_bytes=0)


@pytest.fixture
def db(config):
    database = Database(config.data_dir / "archive.sqlite3", config.instance, config.username)
    seed(database)
    yield database
    database.close()


def seed(database):
    start = int(time.time()) + 10
    records = [
        {"key": {"id": "a1", "remoteJid": CHAT_A, "fromMe": False}, "pushName": "Synthetic Alpha", "messageTimestamp": start, "message": {"conversation": "Cliente 100%_ok"}},
        {"key": {"id": "a2", "remoteJid": CHAT_A, "fromMe": True}, "messageTimestamp": start + 10, "message": {"conversation": "Cliente respondido"}},
        {"key": {"id": "b1", "remoteJid": CHAT_B, "fromMe": False}, "pushName": "Synthetic Beta", "messageTimestamp": start + 20, "message": {"imageMessage": {"caption": "Cliente imagem", "mimetype": "image/jpeg"}}},
        {"key": {"id": "b2", "remoteJid": CHAT_B, "fromMe": True}, "messageTimestamp": start + 30, "message": {"audioMessage": {"mimetype": "audio/ogg"}}},
        {"key": {"id": "c1", "remoteJid": CHAT_C, "fromMe": False}, "pushName": "Synthetic Gamma", "messageTimestamp": start + 40, "message": {"conversation": "Outra mensagem"}},
        {"key": {"id": "a3", "remoteJid": CHAT_A, "fromMe": False}, "pushName": "Synthetic Alpha", "messageTimestamp": start + 50, "message": {"conversation": "Segunda resposta"}},
    ]
    database.ingest({"event": "messages.upsert", "data": records})
    return start


def search(database, **kwargs):
    parameters = {"query": None, "date_from": None, "date_to": None, "chat": None, "message_type": None, "direction": None, "page": 1, "size": 50}
    parameters.update(kwargs)
    return database.search(**parameters)


def test_global_search_all_filters_inclusive_dates_and_identification(db):
    start = db.messages(CHAT_A, "100%_ok", 1, 50)["items"][0]["timestamp"]
    assert search(db, query="cliente")["total"] == 3
    assert search(db, query="cliente", direction="in")["total"] == 2
    assert search(db, query="cliente", chat=CHAT_A, message_type="text", direction="out")["items"][0]["id"] == "a2"
    assert search(db, date_from=start + 10, date_to=start + 20)["total"] == 2
    assert search(db, query="%_")["total"] == 1
    db.set_conversation_preferences(CHAT_B, favorite=True, labels=["Cliente"], archived_local=True)
    image = search(db, query="imagem", message_type="image")["items"][0]
    assert image["type"] == "image" and image["conversation"]["name"] == "Synthetic Beta"
    assert image["conversation"]["favorite"] is True and image["conversation"]["labels"] == ["Cliente"]
    assert image["conversation"]["archived_local"] is True and image["conversation"]["archived_whatsapp"] is None
    # Archiving changes navigation, not global coverage or message existence.
    assert db.counts()["messages"] == 6 and search(db)["total"] == 6


def test_search_pagination_complete_without_overlap_and_missing_timestamps(db):
    pages = [search(db, page=page, size=2) for page in (1, 2, 3)]
    assert all(page["total"] == 6 and page["pages"] == 3 for page in pages)
    keys = [(row["chat"], row["id"]) for page in pages for row in page["items"]]
    assert len(keys) == len(set(keys)) == 6
    assert search(db, page=4, size=2)["items"] == []
    db.ingest({"event": "messages.set", "data": {"key": {"id": "missing-time", "remoteJid": CHAT_C}, "message": {"conversation": "Missing timestamp"}}})
    assert search(db, query="Missing timestamp")["total"] == 1
    assert search(db, query="Missing timestamp", date_from=1)["total"] == 0


def test_local_filters_preserve_existing_name_search_unseen_and_pagination(db):
    db.set_conversation_preferences(CHAT_A, favorite=True, labels=[" Ação ", "ação", "Cliente"])
    db.set_conversation_preferences(CHAT_B, favorite=True, labels=["Ação"], archived_local=True)
    assert db.conversations(1, 50)["total"] == 2
    assert db.conversations(1, 50, archived="archived")["items"][0]["chat"] == CHAT_B
    assert db.conversations(1, 50, favorites_only=True)["total"] == 1
    assert db.conversations(1, 50, favorites_only=True, label="AÇÃO", archived="all")["total"] == 2
    assert db.conversation_labels() == ["Ação", "Cliente"]
    assert db.conversations(1, 50, query="Synthetic Alpha", unseen_only=True, favorites_only=True)["total"] == 1
    assert db.conversations(1, 1, label="ação", archived="all")["pages"] == 2
    assert len(db.conversations(2, 1, label="ação", archived="all")["items"]) == 1
    result = db.set_conversation_preferences(CHAT_A, archived_local=True)
    assert result["favorite"] is True and result["labels"] == ["Ação", "Cliente"]
    assert db.conversations(1, 50)["total"] == 1
    db.set_conversation_preferences(CHAT_A, archived_local=False)
    assert db.conversations(1, 50)["total"] == 2
    assert db.messages(CHAT_A, None, 1, 50)["total"] == 3


def test_preferences_and_events_are_durable_without_modifying_messages(config):
    database = Database(config.data_dir / "archive.sqlite3", config.instance)
    seed(database)
    before = database.messages(None, None, 1, 50)
    captured = database.get_meta("capture_started")
    cursor = database.latest_event_id()
    database.set_conversation_preferences(CHAT_A, favorite=True, labels=["Synthetic label"], archived_local=True)
    assert database.events_since(cursor)[0]["data"]["kind"] == "conversation.preferences"
    database.close()
    reopened = Database(config.data_dir / "archive.sqlite3", config.instance)
    try:
        assert reopened.conversation_preferences(CHAT_A) == {"chat": CHAT_A, "favorite": True, "labels": ["Synthetic label"], "archived_local": True, "archived_whatsapp": None}
        assert reopened.messages(None, None, 1, 50) == before
        assert reopened.get_meta("capture_started") == captured
        assert reopened.conversations(1, 50, archived="archived")["total"] == 1
    finally:
        reopened.close()


def test_preferences_transaction_rolls_back_if_event_cannot_commit(db):
    before_messages = db.messages(None, None, 1, 50)
    before_preference = db.conversation_preferences(CHAT_A)
    db.conn.execute("CREATE TRIGGER synthetic_event_failure BEFORE INSERT ON events BEGIN SELECT RAISE(ABORT,'synthetic failure'); END")
    with pytest.raises(sqlite3.IntegrityError):
        db.set_conversation_preferences(CHAT_A, favorite=True, labels=["Rollback"], archived_local=True)
    assert db.conversation_preferences(CHAT_A) == before_preference
    assert db.messages(None, None, 1, 50) == before_messages
    db.conn.execute("DROP TRIGGER synthetic_event_failure")
    assert db.set_conversation_preferences(CHAT_A, favorite=True)["favorite"] is True


def test_existing_archive_additive_schema_upgrade_preserves_records(config):
    original = Database(config.data_dir / "archive.sqlite3", config.instance)
    seed(original)
    before = original.messages(None, None, 1, 50)
    original.conn.execute("DROP TABLE conversation_preferences")
    original.conn.commit()
    original.close()
    upgraded = Database(config.data_dir / "archive.sqlite3", config.instance)
    try:
        assert upgraded.messages(None, None, 1, 50) == before
        row = upgraded.conversations(1, 50)["items"][0]
        assert row["favorite"] is False and row["labels"] == [] and row["archived_local"] is False
        assert row["archived_whatsapp"] is None
    finally:
        upgraded.close()


def test_api_search_preferences_auth_csrf_validation_and_local_only(config):
    app = create_app(config, NoNetwork(), start_background=False)
    with TestClient(app) as client:
        seed(app.state.db)
        assert client.get("/api/search?q=Cliente").status_code == 401
        assert client.post("/api/conversations/preferences", json={"chat": CHAT_A, "favorite": True}).status_code == 401
        login = client.post("/api/login", json={"username": config.username, "password": config.password})
        csrf = login.json()["csrf"]
        assert client.post("/api/conversations/preferences", json={"chat": CHAT_A, "favorite": True}).status_code == 403
        headers = {"X-Archive-CSRF": csrf}
        result = client.post("/api/conversations/preferences", json={"chat": CHAT_A, "favorite": True, "labels": ["Cliente"], "archived_local": True}, headers=headers)
        assert result.status_code == 200 and result.json()["archived_whatsapp"] is None
        assert client.get("/api/conversations").json()["total"] == 2
        assert client.get("/api/conversations?archived=archived&favorites_only=true&label=cliente").json()["items"][0]["chat"] == CHAT_A
        assert client.get("/api/conversations/labels").json() == {"items": ["Cliente"]}
        search_result = client.get("/api/search", params={"q": "cliente", "chat": CHAT_A, "direction": "out", "type": "text"}).json()
        assert search_result["total"] == 1 and search_result["items"][0]["conversation"]["archived_local"] is True
        invalid_bodies = [{"chat": CHAT_A}, {"chat": CHAT_A, "favorite": None}, {"chat": CHAT_A, "favorite": "true"}, {"chat": CHAT_A, "labels": [" "]}, {"chat": CHAT_A, "labels": ["x" * 65]}, {"chat": CHAT_A, "archived_whatsapp": True}]
        for body in invalid_bodies:
            assert client.post("/api/conversations/preferences", json=body, headers=headers).status_code == 422
        assert client.post("/api/conversations/preferences", json={"chat": "synthetic-unknown", "favorite": True}, headers=headers).status_code == 404
        for parameters in ({"direction": "both"}, {"type": "arbitrary"}, {"date_from": 20, "date_to": 10}, {"date_from": -1}, {"page_size": 201}):
            assert client.get("/api/search", params=parameters).status_code == 422
        assert client.get("/api/conversations?archived=whatsapp").status_code == 422
        assert app.state.db.counts()["messages"] == 6


def test_ping_wal_reader_remains_available_during_locked_writer(db):
    ready, release = threading.Event(), threading.Event()
    captured = db.get_meta("capture_started")

    def hold_writer():
        with db.lock:
            db.conn.execute("BEGIN IMMEDIATE")
            db.conn.execute("UPDATE metadata SET value='0' WHERE key LIKE '%capture_started'")
            ready.set()
            release.wait(3)
            db.conn.rollback()

    writer = threading.Thread(target=hold_writer)
    writer.start()
    try:
        assert ready.wait(1)
        started = time.monotonic()
        assert db.ping() is True
        assert time.monotonic() - started < 1
    finally:
        release.set()
        writer.join(timeout=4)
    assert db.get_meta("capture_started") == captured
    original_path = db.path
    db.path = original_path.parent / "synthetic-nonexistent.sqlite3"
    try:
        assert db.ping() is False
    finally:
        db.path = original_path
