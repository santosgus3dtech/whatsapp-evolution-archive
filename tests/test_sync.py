import asyncio
from dataclasses import replace

import pytest

from archive_service.database import Database
from archive_service.evolution import EvolutionError
from archive_service.settings import Settings
from archive_service.sync import Reconciler


def record(number):
    return {"key": {"remoteJid": "123456@s.whatsapp.net", "id": "synthetic-" + str(number), "fromMe": False}, "message": {"conversation": "Synthetic history"}, "messageTimestamp": 1700000000}


class History:
    def __init__(self, total=5, fail=None):
        self.total, self.fail = total, fail
        self.calls = []

    async def messages(self, page, size):
        self.calls.append(page)
        if page == self.fail:
            raise EvolutionError("evolution_unreachable")
        return {"records": [record(page)] if page <= self.total else [], "currentPage": page, "pages": self.total}


def settings(path, budget=2):
    return Settings(data_dir=path, username="synthetic", password="synthetic-password", webhook_secret="synthetic-secret", evolution_url="http://evolution.test", evolution_key="synthetic-key", instance="synthetic", minimum_free_bytes=0, sync_max_pages=budget)


def test_budget_resume_overlap_and_periodic_full_pass(tmp_path):
    async def scenario():
        config = settings(tmp_path)
        db = Database(tmp_path / "archive.sqlite3", config.instance)
        api = History()
        try:
            sync = Reconciler(db, api, config)
            await sync.start()
            await sync.task
            assert api.calls == [1, 2]
            first = db.get_meta("sync")
            assert first["state"] == "limited" and first["next_page"] == 3
            await sync.start(automatic=True)
            await sync.task
            assert api.calls == [1, 2, 2, 3, 4]
            assert db.get_meta("sync")["next_page"] == 5
            await sync.start(automatic=True)
            await sync.task
            completed = db.get_meta("sync")
            assert api.calls == [1, 2, 2, 3, 4, 4, 5]
            assert completed["state"] == "complete" and completed["incomplete"] is False
            assert completed["coverage_complete"] is False
            assert completed["inserted"] == 5 and db.counts()["messages"] == 5
            assert completed["duplicates"] == 2
            assert len(db.get_meta("sync_runs")) == 3
            await sync.start()
            await sync.task
            fresh = db.get_meta("sync")
            assert fresh["pass_id"] != first["pass_id"] and fresh["resume_from_page"] == 1
            assert fresh["pass_number"] == first["pass_number"] + 1
            assert fresh["inserted"] == 0
        finally:
            db.close()
    asyncio.run(scenario())


def test_error_checkpoint_survives_database_restart(tmp_path):
    async def scenario():
        config = settings(tmp_path, 5)
        db = Database(tmp_path / "archive.sqlite3", config.instance)
        broken = Reconciler(db, History(fail=3), config)
        await broken.start()
        await broken.task
        saved = db.get_meta("sync")
        assert saved["next_page"] == 3 and saved["failed_page"] == 3
        db.close()
        recovered = Database(tmp_path / "archive.sqlite3", config.instance)
        api = History()
        try:
            sync = Reconciler(recovered, api, config)
            await sync.start()
            await sync.task
            state = recovered.get_meta("sync")
            assert api.calls == [2, 3, 4, 5]
            assert state["pass_id"] == saved["pass_id"]
            assert state["inserted"] == 5 and state["run_number"] == 2
            assert recovered.counts()["messages"] == 5
        finally:
            recovered.close()
    asyncio.run(scenario())


def test_one_page_budget_always_advances_and_legacy_checkpoint_migrates(tmp_path):
    async def scenario():
        config = settings(tmp_path, 1)
        db = Database(tmp_path / "archive.sqlite3", config.instance)
        api = History(total=4)
        try:
            db.ingest({"event": "messages.upsert", "data": [record(1), record(2)]}, "reconcile")
            db.set_meta("sync", {"state": "interrupted", "incomplete": True, "current_page": 2, "page_size": 100, "inserted": 2, "processed": 2})
            sync = Reconciler(db, api, config)
            await sync.start()
            await sync.task
            assert api.calls == [2, 3]
            assert db.get_meta("sync")["next_page"] == 4
            await sync.start()
            await sync.task
            assert api.calls == [2, 3, 3, 4]
            assert db.get_meta("sync")["inserted"] == 4
            assert db.get_meta("sync")["state"] == "complete"
        finally:
            db.close()
    asyncio.run(scenario())


def test_invalid_page_does_not_advance_and_partial_ingest_is_deduplicated(tmp_path):
    class InvalidHistory(History):
        async def messages(self, page, size):
            return {"records": [record(1), {}], "currentPage": page, "pages": 1}

    async def scenario():
        config = settings(tmp_path)
        db = Database(tmp_path / "archive.sqlite3", config.instance)
        try:
            broken = Reconciler(db, InvalidHistory(), config)
            await broken.start()
            await broken.task
            assert db.get_meta("sync")["next_page"] == 1
            assert db.get_meta("sync")["error"] == "history_invalid_records"
            repaired = Reconciler(db, History(total=1), config)
            await repaired.start()
            await repaired.task
            assert db.counts()["messages"] == 1
            assert db.get_meta("sync")["inserted"] == 1
        finally:
            db.close()
    asyncio.run(scenario())


def test_cancelled_attempt_resumes_committed_page_without_losing_progress(tmp_path):
    class SlowHistory(History):
        def __init__(self):
            super().__init__(total=3)
            self.pending = asyncio.Event()

        async def messages(self, page, size):
            if page == 2:
                self.pending.set()
                await asyncio.Event().wait()
            return await super().messages(page, size)

    async def scenario():
        config = settings(tmp_path)
        db = Database(tmp_path / "archive.sqlite3", config.instance)
        try:
            api = SlowHistory()
            sync = Reconciler(db, api, config)
            await sync.start()
            assert await sync.start() is False
            await api.pending.wait()
            sync.task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await sync.task
            assert db.get_meta("sync")["state"] == "interrupted"
            assert db.get_meta("sync")["next_page"] == 2
            resumed_api = History(total=3)
            resumed = Reconciler(db, resumed_api, config)
            await resumed.start()
            await resumed.task
            assert resumed_api.calls == [1, 2, 3]
            assert db.counts()["messages"] == 3
        finally:
            db.close()
    asyncio.run(scenario())


def test_page_size_change_starts_full_pass_and_runs_are_bounded(tmp_path):
    async def scenario():
        config = settings(tmp_path, 1)
        db = Database(tmp_path / "archive.sqlite3", config.instance)
        try:
            initial = Reconciler(db, History(), config)
            await initial.start()
            await initial.task
            previous_id = db.get_meta("sync")["pass_id"]
            changed = Reconciler(db, History(total=1), replace(config, sync_page_size=50))
            await changed.start()
            await changed.task
            assert db.get_meta("sync")["pass_id"] != previous_id
            for _ in range(22):
                await changed.start()
                await changed.task
            assert len(db.get_meta("sync_runs")) == 20
            assert db.get_meta("sync_runs")[-1]["run_number"] == 24
        finally:
            db.close()
    asyncio.run(scenario())


@pytest.mark.parametrize("response,code", [
    ({"records": [record(1)], "currentPage": 2, "pages": 3}, "history_page_mismatch"),
    ({"records": [], "currentPage": 1, "pages": 3}, "history_empty_page"),
    ({"records": ["invalid"], "currentPage": 1, "pages": 3}, "evolution_invalid_history"),
])
def test_invalid_pagination_never_advances_checkpoint(tmp_path, response, code):
    class InvalidHistory(History):
        async def messages(self, page, size):
            return response
    async def scenario():
        config = settings(tmp_path)
        db = Database(tmp_path / "archive.sqlite3", config.instance)
        try:
            sync = Reconciler(db, InvalidHistory(), config)
            await sync.start()
            await sync.task
            state = db.get_meta("sync")
            assert state["next_page"] == 1 and state["error"] == code
            assert db.counts()["messages"] == 0
        finally:
            db.close()
    asyncio.run(scenario())


def test_repeated_page_is_detected_across_resumed_attempts(tmp_path):
    class RepeatedHistory(History):
        async def messages(self, page, size):
            return {"records": [record(1)], "currentPage": page, "pages": 3}
    async def scenario():
        config = settings(tmp_path, 1)
        db = Database(tmp_path / "archive.sqlite3", config.instance)
        try:
            sync = Reconciler(db, RepeatedHistory(), config)
            await sync.start()
            await sync.task
            assert db.get_meta("sync")["next_page"] == 2
            await sync.start()
            await sync.task
            assert db.get_meta("sync")["error"] == "history_repeated_page"
            assert db.get_meta("sync")["next_page"] == 2
        finally:
            db.close()
    asyncio.run(scenario())


def test_new_messages_shift_old_fingerprints_without_blocking_resume(tmp_path):
    class MovingHistory:
        def __init__(self):
            self.records = [record(number) for number in range(500, 0, -1)]
            self.calls = []

        async def messages(self, page, size):
            self.calls.append(page)
            begin = (page - 1) * size
            return {"records": self.records[begin:begin + size], "currentPage": page, "pages": (len(self.records) + size - 1) // size, "total": len(self.records)}

    async def scenario():
        config = settings(tmp_path, 2)
        db = Database(tmp_path / "archive.sqlite3", config.instance)
        api = MovingHistory()
        try:
            sync = Reconciler(db, api, config)
            await sync.start()
            await sync.task
            assert db.get_meta("sync")["next_page"] == 3
            assert db.counts()["messages"] == 200
            # One new page shifts old page1 to page2. Its persisted fingerprint
            # is valid data at the new offset, not a repeated-page API failure.
            api.records = [record(number) for number in range(600, 500, -1)] + api.records
            await sync.start()
            await sync.task
            state = db.get_meta("sync")
            assert api.calls == [1, 2, 2, 3, 4]
            assert state["state"] == "limited" and state["next_page"] == 5
            assert state["error"] == "history_page_limit" and state["coverage_complete"] is False
            assert db.counts()["messages"] == 300
            await sync.start()
            await sync.task
            assert db.get_meta("sync")["state"] == "complete"
            assert db.counts()["messages"] == 500
            # The following full pass picks up the newly prepended page. An
            # exhausted source pass was never a full-history coverage claim.
            while True:
                await sync.start()
                await sync.task
                if db.get_meta("sync")["state"] == "complete":
                    break
            assert db.counts()["messages"] == 600
            assert db.get_meta("sync")["coverage_complete"] is False
        finally:
            db.close()
    asyncio.run(scenario())
