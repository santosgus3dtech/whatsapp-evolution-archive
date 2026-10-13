from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any


def timestamp_seconds(value: Any) -> int | None:
    """Accept Evolution seconds, milliseconds and protobuf Long JSON values."""
    if isinstance(value, bool):
        return None
    if isinstance(value, dict):
        if "low" in value:
            try:
                value = (int(value.get("high", 0)) << 32) + (int(value["low"]) & 0xFFFFFFFF)
            except (TypeError, ValueError, OverflowError):
                return None
        elif "seconds" in value:
            value = value["seconds"]
        else:
            return None
    try:
        number = float(value)
        if not math.isfinite(number) or number <= 0:
            return None
        if number > 100_000_000_000:
            number /= 1000
        # Reject microsecond timestamps and wildly future dates.
        if number > 4_102_444_800:
            return None
        return int(number)
    except (ValueError, TypeError, OverflowError):
        return None


def event_name(value: Any) -> str:
    return str(value or "").lower().replace("_", ".")[:64]


def extract_records(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [record for record in data if isinstance(record, dict)]
    if isinstance(data, dict):
        if isinstance(data.get("messages"), list):
            return extract_records(data["messages"])
        if isinstance(data.get("messages"), dict):
            return extract_records(data["messages"].get("records", []))
        if isinstance(data.get("records"), list):
            return extract_records(data["records"])
        if isinstance(data.get("keys"), list):
            return [{"key": key} for key in data["keys"] if isinstance(key, dict)]
        return [data]
    return []


def plain_string(value: Any, maximum: int = 2048) -> str | None:
    return value[:maximum] if isinstance(value, str) else None


def extract_content(record: dict[str, Any]) -> tuple[str, str | None, dict[str, Any]]:
    # Evolution 2.3.7 emits the ProtocolMessage itself for MESSAGES_EDITED.
    message = record.get("editedMessage") or record.get("message")
    message = message if isinstance(message, dict) else {}
    for _ in range(8):
        nested = None
        for wrapper in ("ephemeralMessage", "viewOnceMessage", "viewOnceMessageV2", "viewOnceMessageV2Extension", "documentWithCaptionMessage", "editedMessage"):
            if isinstance(message.get(wrapper), dict):
                nested = message[wrapper].get("message")
                break
        protocol = message.get("protocolMessage")
        if nested is None and isinstance(protocol, dict) and isinstance(protocol.get("editedMessage"), dict):
            nested = protocol["editedMessage"]
        if not isinstance(nested, dict):
            break
        message = nested
    if isinstance(message.get("conversation"), str):
        return "text", message["conversation"][:200000], {}
    if isinstance(message.get("extendedTextMessage"), dict):
        return "text", plain_string(message["extendedTextMessage"].get("text"), 200000), {}
    media = {"imageMessage": "image", "videoMessage": "video", "audioMessage": "audio", "documentMessage": "document", "stickerMessage": "sticker"}
    for name, kind in media.items():
        if isinstance(message.get(name), dict):
            item = message[name]
            metadata: dict[str, Any] = {"has_media": True, "media_saved": False}
            mime = plain_string(item.get("mimetype"), 100)
            if mime and re.fullmatch(r"[A-Za-z0-9.+-]+/[A-Za-z0-9.+-]+", mime):
                metadata["mimetype"] = mime
            for source, target in (("fileLength", "size"), ("seconds", "duration"), ("width", "width"), ("height", "height")):
                value = item.get(source)
                if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
                    metadata[target] = value
            return kind, plain_string(item.get("caption"), 200000), metadata
    for name, field, kind in (("reactionMessage", "text", "reaction"), ("buttonsResponseMessage", "selectedDisplayText", "button"), ("listResponseMessage", "title", "list"), ("pollCreationMessage", "name", "poll"), ("pollCreationMessageV3", "name", "poll")):
        if isinstance(message.get(name), dict):
            return kind, plain_string(message[name].get(field), 200000), {}
    # Persist only known type names; never retain unknown payloads or media secrets.
    for name, kind in (("locationMessage", "location"), ("liveLocationMessage", "location"), ("contactMessage", "contact"), ("contactsArrayMessage", "contacts"), ("protocolMessage", "system")):
        if name in message:
            return kind, None, {}
    return "unknown", None, {}


class Database:
    def __init__(self, path: Path, instance: str, legacy_username: str = "legacy"):
        self.path = path
        self.instance = instance
        self.legacy_username = legacy_username
        self.lock = threading.RLock()
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False, timeout=15)
        self.conn.row_factory = sqlite3.Row
        self.conn.create_function("unicode_casefold", 1, lambda value: value.casefold() if isinstance(value, str) else "", deterministic=True)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=FULL")
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS messages (
                instance TEXT NOT NULL, chat TEXT NOT NULL, id TEXT NOT NULL,
                from_me INTEGER NOT NULL, participant TEXT, push_name TEXT, type TEXT NOT NULL,
                text TEXT, timestamp INTEGER, first_seen_at INTEGER NOT NULL,
                last_seen_at INTEGER NOT NULL, source TEXT NOT NULL,
                historical INTEGER NOT NULL, received_new INTEGER NOT NULL,
                seen_at INTEGER, edited INTEGER NOT NULL DEFAULT 0,
                deleted INTEGER NOT NULL DEFAULT 0, original_received INTEGER NOT NULL DEFAULT 1,
                metadata TEXT NOT NULL DEFAULT '{}',
                PRIMARY KEY(instance, chat, id)
            );
            CREATE INDEX IF NOT EXISTS messages_timeline ON messages(instance, chat, timestamp DESC, id);
            CREATE INDEX IF NOT EXISTS messages_unseen ON messages(instance, seen_at, received_new);
            CREATE INDEX IF NOT EXISTS messages_search_filters ON messages(instance, type, from_me, timestamp DESC);
            CREATE TABLE IF NOT EXISTS conversation_preferences (
                instance TEXT NOT NULL, chat TEXT NOT NULL,
                favorite INTEGER NOT NULL DEFAULT 0,
                labels TEXT NOT NULL DEFAULT '[]',
                archived_local INTEGER NOT NULL DEFAULT 0,
                archived_whatsapp INTEGER,
                updated_at INTEGER NOT NULL,
                PRIMARY KEY(instance, chat)
            );
            CREATE INDEX IF NOT EXISTS conversation_preferences_filters ON conversation_preferences(instance, archived_local, favorite, chat);
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT, created_at INTEGER NOT NULL,
                instance TEXT NOT NULL, payload TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS events_instance ON events(instance, id);
            CREATE TABLE IF NOT EXISTS receipts (
                id INTEGER PRIMARY KEY AUTOINCREMENT, instance TEXT NOT NULL,
                event TEXT NOT NULL, received_at INTEGER NOT NULL,
                source TEXT NOT NULL, summary TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY, csrf TEXT NOT NULL, expires_at INTEGER NOT NULL,
                username TEXT
            );
        """)
        if "push_name" not in {row[1] for row in self.conn.execute("PRAGMA table_info(messages)")}:
            self.conn.execute("ALTER TABLE messages ADD COLUMN push_name TEXT")
            self.conn.commit()
        if "original_received" not in {row[1] for row in self.conn.execute("PRAGMA table_info(messages)")}:
            self.conn.execute("ALTER TABLE messages ADD COLUMN original_received INTEGER NOT NULL DEFAULT 1")
            self.conn.commit()
        if "username" not in {row[1] for row in self.conn.execute("PRAGMA table_info(sessions)")}:
            self.conn.execute("ALTER TABLE sessions ADD COLUMN username TEXT")
        self.conn.execute("UPDATE sessions SET username=? WHERE username IS NULL OR username=''", (legacy_username,))
        self.conn.commit()
        if self.get_meta("capture_started") is None:
            self.set_meta("capture_started", int(time.time()))
        sync = self.get_meta("sync")
        if sync and sync.get("state") == "running":
            self.set_meta("sync", {**sync, "state": "interrupted", "incomplete": True, "error": "service_restarted", "finished_at": int(time.time())})

    def close(self) -> None:
        with self.lock:
            self.conn.close()

    def ping(self) -> bool:
        """Probe a separate WAL reader without waiting on the shared writer lock."""
        connection = None
        try:
            connection = sqlite3.connect(self.path.resolve().as_uri() + "?mode=ro", uri=True, timeout=0.5)
            connection.execute("SELECT key FROM metadata LIMIT 1").fetchone()
            return True
        except (sqlite3.DatabaseError, OSError):
            return False
        finally:
            if connection is not None:
                connection.close()

    def get_meta(self, key: str, default: Any = None) -> Any:
        with self.lock:
            row = self.conn.execute("SELECT value FROM metadata WHERE key=?", (self.instance + ":" + key,)).fetchone()
            return json.loads(row[0]) if row else default

    def _meta(self, key: str, value: Any) -> None:
        self.conn.execute("INSERT INTO metadata(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (self.instance + ":" + key, json.dumps(value, ensure_ascii=False)))

    def set_meta(self, key: str, value: Any, notify: bool = False) -> None:
        with self.lock, self.conn:
            self._meta(key, value)
            if notify:
                self._event({"kind": key, key: value})

    def _event(self, payload: dict[str, Any]) -> None:
        self.conn.execute("INSERT INTO events(created_at,instance,payload) VALUES(?,?,?)", (int(time.time()), self.instance, json.dumps(payload, ensure_ascii=False)))

    def _counts(self) -> dict[str, int]:
        row = self.conn.execute("""SELECT count(*) messages, count(DISTINCT chat) conversations,
            coalesce(sum(CASE WHEN received_new=1 AND seen_at IS NULL THEN 1 ELSE 0 END),0) unseen,
            coalesce(sum(received_new),0) received_new FROM messages WHERE instance=?""", (self.instance,)).fetchone()
        return dict(row)

    def counts(self) -> dict[str, int]:
        with self.lock:
            return self._counts()

    def coverage(self) -> dict[str, Any]:
        with self.lock:
            row = self.conn.execute("SELECT min(timestamp), max(timestamp) FROM messages WHERE instance=?", (self.instance,)).fetchone()
            return {"first_message_at": row[0], "last_message_at": row[1], "complete": False, "label": "Somente mensagens disponibilizadas pela Evolution API; histórico completo não verificado."}

    def ingest(self, envelope: dict[str, Any], source: str = "webhook") -> dict[str, Any]:
        event = event_name(envelope.get("event"))
        if event not in {"connection.update", "messages.set", "messages.upsert", "messages.update", "messages.edited", "messages.delete", "send.message"}:
            event = "unknown"
        data = envelope.get("data", {})
        records = extract_records(data)
        now = int(time.time())
        summary: dict[str, Any] = {"inserted": 0, "updated": 0, "duplicates": 0, "invalid": 0, "received_new": 0}
        changes: list[dict[str, Any]] = []
        with self.lock, self.conn:
            if event == "connection.update":
                state = data.get("state", "unknown") if isinstance(data, dict) else "unknown"
                if not isinstance(state, str) or state not in {"open", "close", "connecting"}:
                    state = "unknown"
                self._meta("connection", {"instance": self.instance, "state": state, "updated_at": now})
                changes.append({"kind": "connection", "connection": {"state": state}})
            elif event in {"messages.set", "messages.upsert", "messages.update", "messages.edited", "messages.delete", "send.message"}:
                capture = self.get_meta("capture_started")
                for record in records:
                    key = record.get("key")
                    key = key if isinstance(key, dict) else record
                    chat = plain_string(key.get("remoteJid"))
                    # MESSAGES_UPDATE uses keyId; messageId is the upstream DB UUID.
                    message_id = plain_string(key.get("id") if key is not record else record.get("keyId") or record.get("id"))
                    original_chat = chat
                    alternate_chat = plain_string(key.get("remoteJidAlt"))
                    if chat and chat.endswith("@lid") and alternate_chat and alternate_chat.endswith("@s.whatsapp.net"):
                        chat = alternate_chat
                    protocol = record.get("message", {}).get("protocolMessage") if isinstance(record.get("message"), dict) else None
                    if event == "messages.edited" and isinstance(protocol, dict) and isinstance(protocol.get("key"), dict):
                        key = protocol["key"]
                        chat = plain_string(key.get("remoteJid")) or chat
                        message_id = plain_string(key.get("id")) or message_id
                    if chat and chat.endswith("@lid") and message_id:
                        mapped = self.conn.execute("SELECT chat FROM messages WHERE instance=? AND id=? AND json_extract(metadata,'$.original_chat')=? LIMIT 1", (self.instance, message_id, chat)).fetchone()
                        if mapped:
                            chat = mapped["chat"]
                    if not chat or not message_id:
                        summary["invalid"] += 1
                        continue
                    existing = self.conn.execute("SELECT * FROM messages WHERE instance=? AND chat=? AND id=?", (self.instance, chat, message_id)).fetchone()
                    kind, text, metadata = extract_content(record)
                    if original_chat and original_chat != chat:
                        metadata["original_chat"] = original_chat
                    status = record.get("status")
                    if isinstance(status, str) and status in {"ERROR", "PENDING", "SERVER_ACK", "DELIVERY_ACK", "READ", "PLAYED", "EDITED", "DELETED"}:
                        metadata["whatsapp_status"] = status
                    edited = event == "messages.edited" or status == "EDITED"
                    deleted = event == "messages.delete" or status == "DELETED" or key.get("deleted") is True
                    timestamp = timestamp_seconds(record.get("messageTimestamp"))
                    notification_type = record.get("type") or (data.get("type") if isinstance(data, dict) else None)
                    historical = event != "messages.upsert" or timestamp is None or timestamp < capture or (source == "webhook" and notification_type is not None and notification_type != "notify")
                    from_me = key.get("fromMe") is True
                    received_new = not historical and not from_me
                    participant = plain_string(key.get("participant") or record.get("participant"))
                    push_name = plain_string(record.get("pushName"), 200)
                    original_received = event in {"messages.set", "messages.upsert", "send.message"}
                    restored = bool(existing and not existing["original_received"] and original_received)
                    if existing:
                        # A delayed original/backfill must not undo an edit already archived.
                        new_text = text if text is not None and (not existing["edited"] or edited) else existing["text"]
                        new_kind = kind if kind != "unknown" else existing["type"]
                        new_timestamp = timestamp if timestamp is not None else existing["timestamp"]
                        new_metadata = json.dumps({**json.loads(existing["metadata"]), **metadata}, sort_keys=True)
                        has_changed = (restored or new_text != existing["text"] or new_kind != existing["type"] or new_timestamp != existing["timestamp"] or new_metadata != existing["metadata"] or (push_name and push_name != existing["push_name"]) or (edited and not existing["edited"]) or (deleted and not existing["deleted"]))
                        if not has_changed:
                            summary["duplicates"] += 1
                            continue
                        self.conn.execute("""UPDATE messages SET text=?,type=?,timestamp=?,metadata=?,last_seen_at=?,edited=?,deleted=?
                            WHERE instance=? AND chat=? AND id=?""", (new_text, new_kind, new_timestamp, new_metadata, now, int(edited or existing["edited"]), int(deleted or existing["deleted"]), self.instance, chat, message_id))
                        if push_name:
                            self.conn.execute("UPDATE messages SET push_name=? WHERE instance=? AND chat=? AND id=?", (push_name, self.instance, chat, message_id))
                        if restored:
                            self.conn.execute("""UPDATE messages SET original_received=1,from_me=?,participant=?,source=?,historical=?,received_new=?,seen_at=?
                                WHERE instance=? AND chat=? AND id=?""", (int(from_me), participant, source, int(historical), int(received_new), None if received_new else now, self.instance, chat, message_id))
                            summary["received_new"] += int(received_new)
                        summary["updated"] += 1
                    else:
                        # Updates/deletes may arrive before the original. Keep a non-notifying tombstone.
                        self.conn.execute("""INSERT INTO messages(instance,chat,id,from_me,participant,push_name,type,text,timestamp,first_seen_at,last_seen_at,source,historical,received_new,seen_at,edited,deleted,original_received,metadata)
                            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (self.instance, chat, message_id, int(from_me), participant, push_name, kind, text, timestamp, now, now, source, int(historical), int(received_new), None if received_new else now, int(edited), int(deleted), int(original_received), json.dumps(metadata, sort_keys=True)))
                        summary["inserted"] += 1
                        summary["received_new"] += int(received_new)
                    changes.append({"kind": "message", "chat": chat, "message_id": message_id, "received_new": bool(received_new and (not existing or restored)), "historical": bool(historical), "source": source})
                if event == "messages.set":
                    history_metadata = {"received_at": now}
                    for key_name in ("isLatest", "progress"):
                        value = envelope.get(key_name, data.get(key_name) if isinstance(data, dict) else None)
                        if isinstance(value, (int, float, bool)):
                            history_metadata[key_name] = value
                    self._meta("history_signal", history_metadata)
            else:
                summary["ignored"] = True
            # Whitelisted summary only: tokens, URLs, headers and raw media never enter SQLite.
            self.conn.execute("INSERT INTO receipts(instance,event,received_at,source,summary) VALUES(?,?,?,?,?)", (self.instance, event, now, source, json.dumps(summary)))
            if changes:
                counts = self._counts()
                # Historical batches need a refresh, not one notification per old message.
                if source != "webhook" or len(changes) > 100:
                    self._event({"kind": "archive.changed", "counts": counts, "unseen": counts["unseen"], **summary})
                else:
                    for change in changes:
                        self._event({**change, "counts": counts, "unseen": counts["unseen"]})
        return summary

    @staticmethod
    def _serialize(row: sqlite3.Row) -> dict[str, Any]:
        result = dict(row)
        for key in ("from_me", "historical", "received_new", "edited", "deleted"):
            result[key] = bool(result[key])
        result["seen"] = result.pop("seen_at") is not None
        result.pop("original_received", None)
        result["metadata"] = json.loads(result["metadata"])
        return result

    def messages(self, chat: str | None, query: str | None, page: int, size: int) -> dict[str, Any]:
        where = "instance=?"
        params: list[Any] = [self.instance]
        if chat:
            where += " AND chat=?"
            params.append(chat)
        if query:
            where += " AND text LIKE ? ESCAPE '\\'"
            params.append("%" + query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%")
        with self.lock:
            total = self.conn.execute("SELECT count(*) FROM messages WHERE " + where, params).fetchone()[0]
            rows = self.conn.execute("SELECT * FROM messages WHERE " + where + " ORDER BY coalesce(timestamp,0) DESC,first_seen_at DESC,id DESC LIMIT ? OFFSET ?", [*params, size, (page - 1) * size]).fetchall()
            return {"items": [self._serialize(row) for row in rows], "total": total, "page": page, "page_size": size, "pages": math.ceil(total / size)}

    @staticmethod
    def _like_pattern(query: str) -> str:
        return "%" + query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"

    @staticmethod
    def _preference_fields(row: dict[str, Any] | sqlite3.Row | None) -> dict[str, Any]:
        values = dict(row) if row else {}
        state = values.get("archived_whatsapp")
        return {
            "favorite": bool(values.get("favorite", False)),
            "labels": json.loads(values.get("labels") or "[]"),
            "archived_local": bool(values.get("archived_local", False)),
            "archived_whatsapp": None if state is None else bool(state),
        }

    def conversation_preferences(self, chat: str) -> dict[str, Any]:
        with self.lock:
            row = self.conn.execute("SELECT favorite,labels,archived_local,archived_whatsapp FROM conversation_preferences WHERE instance=? AND chat=?", (self.instance, chat)).fetchone()
            return {"chat": chat, **self._preference_fields(row)}

    def set_conversation_preferences(self, chat: str, favorite: bool | None = None, labels: list[str] | None = None, archived_local: bool | None = None) -> dict[str, Any]:
        if not isinstance(chat, str) or not chat or len(chat) > 2048:
            raise ValueError("invalid_conversation_preferences")
        if any(value is not None and type(value) is not bool for value in (favorite, archived_local)):
            raise ValueError("invalid_conversation_preferences")
        normalized: list[str] | None = None
        if labels is not None:
            if not isinstance(labels, list) or len(labels) > 20:
                raise ValueError("invalid_conversation_labels")
            normalized, keys = [], set()
            for value in labels:
                if not isinstance(value, str):
                    raise ValueError("invalid_conversation_labels")
                value = value.strip()
                if not value or len(value) > 64 or any(ord(character) < 32 or ord(character) == 127 for character in value):
                    raise ValueError("invalid_conversation_labels")
                if value.casefold() not in keys:
                    normalized.append(value)
                    keys.add(value.casefold())
        with self.lock, self.conn:
            exists = self.conn.execute("SELECT 1 FROM messages WHERE instance=? AND chat=? LIMIT 1", (self.instance, chat)).fetchone()
            if not exists:
                raise LookupError("conversation_not_found")
            current = self.conversation_preferences(chat)
            result = {
                **current,
                "favorite": current["favorite"] if favorite is None else favorite,
                "labels": current["labels"] if normalized is None else normalized,
                "archived_local": current["archived_local"] if archived_local is None else archived_local,
            }
            if result == current:
                return result
            self.conn.execute("""INSERT INTO conversation_preferences(instance,chat,favorite,labels,archived_local,updated_at)
                VALUES(?,?,?,?,?,?) ON CONFLICT(instance,chat) DO UPDATE SET favorite=excluded.favorite,
                labels=excluded.labels,archived_local=excluded.archived_local,updated_at=excluded.updated_at""",
                (self.instance, chat, int(result["favorite"]), json.dumps(result["labels"], ensure_ascii=False), int(result["archived_local"]), int(time.time())))
            self._event({"kind": "conversation.preferences", "chat": chat, "preferences": result})
            return result

    def conversation_labels(self) -> list[str]:
        with self.lock:
            rows = self.conn.execute("SELECT value FROM conversation_preferences p,json_each(p.labels) WHERE p.instance=?", (self.instance,)).fetchall()
            labels: dict[str, str] = {}
            for row in rows:
                value = row["value"]
                if isinstance(value, str):
                    labels.setdefault(value.casefold(), value)
            return [labels[key] for key in sorted(labels)]

    def search(self, query: str | None, date_from: int | None, date_to: int | None, chat: str | None, message_type: str | None, direction: str | None, page: int, size: int) -> dict[str, Any]:
        if date_from is not None and date_to is not None and date_from > date_to:
            raise ValueError("invalid_date_range")
        if direction not in {None, "in", "out"}:
            raise ValueError("invalid_direction")
        where, params = "m.instance=?", [self.instance]
        if query:
            where += " AND m.text LIKE ? ESCAPE '\\'"
            params.append(self._like_pattern(query))
        for value, clause in ((date_from, "m.timestamp>=?"), (date_to, "m.timestamp<=?"), (chat, "m.chat=?"), (message_type, "m.type=?")):
            if value is not None:
                where += " AND " + clause
                params.append(value)
        if direction:
            where += " AND m.from_me=?"
            params.append(int(direction == "out"))
        with self.lock:
            total = self.conn.execute("SELECT count(*) FROM messages m WHERE " + where, params).fetchone()[0]
            rows = self.conn.execute("""SELECT m.*,p.favorite,p.labels,p.archived_local,p.archived_whatsapp,
                (SELECT n.push_name FROM messages n WHERE n.instance=m.instance AND n.chat=m.chat AND n.from_me=0
                 AND n.push_name IS NOT NULL AND n.push_name<>'' AND m.chat NOT LIKE '%@g.us'
                 ORDER BY n.timestamp DESC,n.first_seen_at DESC,n.id DESC LIMIT 1) conversation_push_name
                FROM messages m LEFT JOIN conversation_preferences p ON p.instance=m.instance AND p.chat=m.chat
                WHERE """ + where + " ORDER BY coalesce(m.timestamp,0) DESC,m.first_seen_at DESC,m.chat,m.id DESC LIMIT ? OFFSET ?", [*params, size, (page - 1) * size]).fetchall()
            items = []
            for row in rows:
                item = self._serialize(row)
                name = item.pop("conversation_push_name")
                preferences = self._preference_fields({key: item.pop(key) for key in ("favorite", "labels", "archived_local", "archived_whatsapp")})
                item["conversation"] = {"chat": item["chat"], "name": name or item["chat"].split("@")[0], "push_name": name, **preferences}
                items.append(item)
            return {"items": items, "total": total, "page": page, "page_size": size, "pages": math.ceil(total / size)}

    def conversations(self, page: int, size: int, query: str | None = None, unseen_only: bool = False, favorites_only: bool = False, label: str | None = None, archived: str = "active") -> dict[str, Any]:
        if archived not in {"active", "archived", "all"}:
            raise ValueError("invalid_archive_filter")
        where = "m.instance=?"
        params: list[Any] = [self.instance]
        if unseen_only:
            where += " AND m.chat IN (SELECT chat FROM messages WHERE instance=? AND received_new=1 AND seen_at IS NULL)"
            params.append(self.instance)
        if favorites_only:
            where += " AND p.favorite=1"
        if archived != "all":
            where += " AND coalesce(p.archived_local,0)=?"
            params.append(int(archived == "archived"))
        if label:
            where += " AND EXISTS(SELECT 1 FROM json_each(coalesce(p.labels,'[]')) WHERE unicode_casefold(value)=?)"
            params.append(label.casefold())
        if query:
            where += " AND m.chat IN (SELECT chat FROM messages WHERE instance=? AND (chat LIKE ? ESCAPE '\\' OR push_name LIKE ? ESCAPE '\\'))"
            pattern = self._like_pattern(query)
            params.extend((self.instance, pattern, pattern))
        joined = " FROM messages m LEFT JOIN conversation_preferences p ON p.instance=m.instance AND p.chat=m.chat WHERE " + where
        with self.lock:
            total = self.conn.execute("SELECT count(DISTINCT m.chat)" + joined, params).fetchone()[0]
            rows = self.conn.execute("""WITH ranked AS (
                SELECT m.instance,m.chat,m.text,m.type,m.timestamp,p.favorite,p.labels,p.archived_local,p.archived_whatsapp,
                    count(*) OVER (PARTITION BY m.chat) messages,
                    sum(CASE WHEN m.received_new=1 AND m.seen_at IS NULL THEN 1 ELSE 0 END) OVER(PARTITION BY m.chat) unseen,
                    sum(m.received_new) OVER(PARTITION BY m.chat) received_new,
                    row_number() OVER(PARTITION BY m.chat ORDER BY coalesce(m.timestamp,0) DESC,m.first_seen_at DESC,m.id DESC) rn
                """ + joined + """
            ) SELECT r.chat,
                (SELECT n.push_name FROM messages n WHERE n.instance=r.instance AND n.chat=r.chat AND n.from_me=0
                 AND n.push_name IS NOT NULL AND n.push_name<>'' AND r.chat NOT LIKE '%@g.us'
                 ORDER BY n.timestamp DESC,n.first_seen_at DESC,n.id DESC LIMIT 1) push_name,
                r.text last_text,r.type last_type,r.timestamp last_message_at,r.messages,r.unseen,r.received_new,r.favorite,r.labels,r.archived_local,r.archived_whatsapp
            FROM ranked r WHERE r.rn=1 ORDER BY coalesce(r.timestamp,0) DESC,r.chat LIMIT ? OFFSET ?""", [*params, size, (page - 1) * size]).fetchall()
            return {"items": [{**dict(row), **self._preference_fields(row)} for row in rows], "total": total, "page": page, "page_size": size, "pages": math.ceil(total / size)}

    def mark_seen(self, chat: str | None, ids: list[str] | None) -> dict[str, int]:
        where = "instance=? AND seen_at IS NULL"
        params: list[Any] = [self.instance]
        if chat:
            where += " AND chat=?"
            params.append(chat)
        if ids is not None:
            if not ids:
                return {"marked": 0, "unseen": self.counts()["unseen"]}
            where += " AND id IN (" + ",".join("?" for _ in ids) + ")"
            params.extend(ids)
        with self.lock, self.conn:
            changed = self.conn.execute("UPDATE messages SET seen_at=? WHERE " + where, [int(time.time()), *params]).rowcount
            self._meta("seen_cursor", self.latest_event_id())
            counts = self._counts()
            if changed:
                self._event({"kind": "seen", "chat": chat, "unseen": counts["unseen"], "counts": counts})
            return {"marked": changed, "unseen": counts["unseen"]}

    def latest_event_id(self) -> int:
        with self.lock:
            return self.conn.execute("SELECT coalesce(max(id),0) FROM events WHERE instance=?", (self.instance,)).fetchone()[0]

    def events_since(self, cursor: int, limit: int = 100) -> list[dict[str, Any]]:
        with self.lock:
            rows = self.conn.execute("SELECT id,payload FROM events WHERE instance=? AND id>? ORDER BY id LIMIT ?", (self.instance, cursor, limit)).fetchall()
            return [{"id": row["id"], "data": json.loads(row["payload"])} for row in rows]

    def add_session(self, token: str, csrf: str, expires: int, username: str | None = None) -> None:
        with self.lock, self.conn:
            self.conn.execute("DELETE FROM sessions WHERE expires_at<=?", (int(time.time()),))
            self.conn.execute("INSERT INTO sessions(token_hash,csrf,expires_at,username) VALUES(?,?,?,?)", (hashlib.sha256(token.encode()).hexdigest(), csrf, expires, username or self.legacy_username))

    def session(self, token: str) -> dict[str, Any] | None:
        with self.lock:
            row = self.conn.execute("SELECT csrf,expires_at,username FROM sessions WHERE token_hash=? AND expires_at>?", (hashlib.sha256(token.encode()).hexdigest(), int(time.time()))).fetchone()
            return dict(row) if row else None

    def delete_session(self, token: str) -> None:
        with self.lock, self.conn:
            self.conn.execute("DELETE FROM sessions WHERE token_hash=?", (hashlib.sha256(token.encode()).hexdigest(),))
