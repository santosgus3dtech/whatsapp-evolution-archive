"""Durable, read-only reconciliation of history exposed by Evolution.

Offset pagination is not a snapshot. Replays overlap one committed page and a
finished pass is followed by another full pass. Neither proves WhatsApp history
is complete; all records go through the existing idempotent database writer.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import shutil
import time
import uuid
from contextlib import suppress
from typing import Any

from fastapi import HTTPException

from .database import Database
from .evolution import EvolutionClient, EvolutionError
from .settings import Settings


CHECKPOINT_VERSION = 2
RUN_HISTORY_LIMIT = 20


def require_storage(settings: Settings) -> None:
    try:
        blocked = shutil.disk_usage(settings.data_dir).free < settings.minimum_free_bytes
    except OSError:
        blocked = True
    if blocked:
        raise HTTPException(503, detail="storage_below_minimum")


def _integer(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int) and value >= 0:
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return default


class Reconciler:
    def __init__(self, db: Database, evolution: EvolutionClient, settings: Settings):
        self.db, self.evolution, self.settings = db, evolution, settings
        self.task: asyncio.Task | None = None
        self.start_lock = asyncio.Lock()

    async def _thread(self, function, *args, **kwargs):
        # Cancelling asyncio.to_thread cannot stop SQLite work. Wait for it before
        # shutdown closes the database; replay handles any uncheckpointed commit.
        worker = asyncio.create_task(asyncio.to_thread(function, *args, **kwargs))
        try:
            return await asyncio.shield(worker)
        except asyncio.CancelledError:
            with suppress(Exception):
                await worker
            raise

    async def _save(self, state: dict[str, Any]) -> None:
        await self._thread(self.db.set_meta, "sync", state, notify=True)
        runs = await self._thread(self.db.get_meta, "sync_runs", [])
        runs = runs if isinstance(runs, list) else []
        # Store only progress/error codes, never JIDs, records or upstream URLs.
        run = {key: state.get(key) for key in (
            "run_id", "run_number", "pass_id", "pass_number", "state",
            "started_at", "finished_at", "resume_from_page", "next_page",
            "current_page", "pages", "processed", "inserted", "updated",
            "duplicates", "run_pages", "automatic", "incomplete", "error",
            "upstream_status", "failed_page",
        )}
        runs = [old for old in runs if isinstance(old, dict) and old.get("run_id") != state["run_id"]]
        await self._thread(self.db.set_meta, "sync_runs", (runs + [run])[-RUN_HISTORY_LIMIT:])

    async def start(self, automatic: bool = False) -> bool:
        async with self.start_lock:
            if self.task and not self.task.done():
                return False
            await asyncio.to_thread(require_storage, self.settings)
            previous = await self._thread(self.db.get_meta, "sync", {})
            previous = previous if isinstance(previous, dict) else {}
            resume = (
                previous.get("checkpoint_version") in {None, CHECKPOINT_VERSION}
                and previous.get("state") in {"running", "interrupted", "limited", "error", "blocked"}
                and previous.get("incomplete") is True
                and previous.get("page_size") == self.settings.sync_page_size
            )
            now = int(time.time())
            # The original reconciler persisted current_page only. Rechecking
            # that page also covers a partially valid legacy ingest on upgrade.
            legacy_next = _integer(previous.get("current_page")) + 1
            next_page = max(1, _integer(previous.get("next_page"), legacy_next)) if resume else 1
            state = {
                "checkpoint_version": CHECKPOINT_VERSION,
                "run_id": uuid.uuid4().hex,
                "run_number": _integer(previous.get("run_number")) + 1,
                "pass_id": (previous.get("pass_id") or uuid.uuid4().hex) if resume else uuid.uuid4().hex,
                "pass_number": max(1, _integer(previous.get("pass_number"))) if resume else _integer(previous.get("pass_number")) + 1,
                "pass_started_at": previous.get("pass_started_at", now) if resume else now,
                "state": "running", "started_at": now, "finished_at": None,
                "incomplete": True, "coverage_complete": False, "error": None,
                "automatic": automatic, "resumed": resume,
                "page_size": self.settings.sync_page_size, "max_pages": self.settings.sync_max_pages,
                "next_page": next_page, "resume_from_page": max(1, next_page - 1),
                "current_page": next_page - 1,
                "pages": _integer(previous.get("pages")) if resume else 0,
                "run_pages": 0,
                "checkpoint_updated_at": previous.get("checkpoint_updated_at") if resume else None,
                "recent_pages": previous.get("recent_pages", [])[-4:] if resume and isinstance(previous.get("recent_pages"), list) else [],
                **{key: _integer(previous.get(key)) if resume else 0 for key in ("processed", "inserted", "updated", "duplicates")},
            }
            await self._save(state)
            self.task = asyncio.create_task(self.run(), name="archive-history-reconciliation")
            return True

    async def run(self) -> None:
        state = await self._thread(self.db.get_meta, "sync")
        page = state["resume_from_page"]
        # The overlap does not consume the budget for new pages. A one-page
        # budget must still advance after a restart rather than replay forever.
        stop = state["next_page"] + self.settings.sync_max_pages
        # Old hashes belong to a different offset view: new messages can move
        # an entire committed page to another legitimate page number. Detect a
        # broken endpoint only from responses observed in this attempt. The
        # extra overlap still makes this check work with a one-page budget.
        fingerprints: dict[str, int] = {}
        try:
            for page in range(page, stop):
                await asyncio.to_thread(require_storage, self.settings)
                result = await self.evolution.messages(page, self.settings.sync_page_size)
                records = result.get("records") if isinstance(result, dict) else None
                if not isinstance(records, list) or any(not isinstance(record, dict) for record in records):
                    raise EvolutionError("evolution_invalid_history")
                total_pages = _integer(result.get("pages"))
                if result.get("currentPage") is not None and str(result["currentPage"]) != str(page):
                    raise EvolutionError("history_page_mismatch")
                if not records and total_pages > page:
                    raise EvolutionError("history_empty_page")
                identity = [(record.get("key", {}).get("remoteJid"), record.get("key", {}).get("id")) for record in records if isinstance(record.get("key"), dict)]
                fingerprint = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
                if records and fingerprint in fingerprints and fingerprints[fingerprint] != page:
                    raise EvolutionError("history_repeated_page")
                await asyncio.to_thread(require_storage, self.settings)
                summary = await self._thread(self.db.ingest, {"event": "messages.upsert", "data": records}, "reconcile")
                state["processed"] += len(records)
                for key in ("inserted", "updated", "duplicates"):
                    state[key] += _integer(summary.get(key))
                # Invalid pages may have partially committed valid records. Do
                # not advance; the next attempt safely replays their duplicates.
                if summary.get("invalid"):
                    raise EvolutionError("history_invalid_records")
                fingerprints[fingerprint] = page
                recent = [item for item in state["recent_pages"] if isinstance(item, dict) and item.get("page") != page]
                state.update(
                    next_page=max(state["next_page"], page + 1), current_page=page,
                    pages=total_pages or page, run_pages=state["run_pages"] + 1,
                    checkpoint_updated_at=int(time.time()),
                    recent_pages=(recent + [{"page": page, "hash": fingerprint}])[-4:],
                )
                await self._save(state)
                if not records or (total_pages and page >= total_pages) or (not total_pages and len(records) < self.settings.sync_page_size):
                    state.update(state="complete", incomplete=False)
                    break
            else:
                state.update(state="limited", error="history_page_limit")
        except asyncio.CancelledError:
            state.update(state="interrupted", incomplete=True, error="service_stopped", failed_page=page)
            raise
        except HTTPException:
            state.update(state="blocked", incomplete=True, error="storage_below_minimum", failed_page=page)
        except EvolutionError as error:
            state.update(state="error", incomplete=True, error=error.code, failed_page=page)
            if error.status is not None:
                state["upstream_status"] = error.status
        except Exception:
            state.update(state="error", incomplete=True, error="history_internal_error", failed_page=page)
        finally:
            state["finished_at"] = int(time.time())
            with suppress(Exception):
                await self._save(state)

    async def periodic(self) -> None:
        await asyncio.sleep(3)
        while True:
            try:
                connection = await self.evolution.connection()
                await self._thread(self.db.set_meta, "connection", {**connection, "updated_at": int(time.time())}, notify=True)
                # Reads of Evolution's stored history also work while WhatsApp
                # is disconnected. Never reconnect/reset the operational instance.
                await self.start(automatic=True)
            except EvolutionError as error:
                await self._thread(self.db.set_meta, "connection", {"instance": self.settings.instance, "state": "unknown", "error": error.code, "updated_at": int(time.time())}, notify=True)
            except HTTPException:
                pass
            except asyncio.CancelledError:
                raise
            except Exception:
                with suppress(Exception):
                    await self._thread(self.db.set_meta, "connection", {"instance": self.settings.instance, "state": "unknown", "error": "connection_internal_error", "updated_at": int(time.time())}, notify=True)
            await asyncio.sleep(self.settings.sync_interval)
