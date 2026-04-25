from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.thread_storage import ThreadStorage


def _build_state(user_id: str, thread_id: str) -> ThreadState:
    return ThreadState(
        thread_id=thread_id,
        user_id=user_id,
        core_direction="topic",
        phase="clarify",
    )


def test_save_and_load_active_roundtrip(tmp_path: Path) -> None:
    storage = ThreadStorage(storage_dir=tmp_path / "threads")
    state = _build_state("u1", "t1")
    storage.save_active(state)
    loaded = storage.load_active("u1")
    assert loaded is not None
    assert loaded.thread_id == "t1"


def test_load_active_missing_returns_none(tmp_path: Path) -> None:
    storage = ThreadStorage(storage_dir=tmp_path / "threads")
    assert storage.load_active("missing") is None


def test_archive_thread_accumulates(tmp_path: Path) -> None:
    storage = ThreadStorage(storage_dir=tmp_path / "threads")
    storage.archive_thread(_build_state("u1", "t1"))
    storage.archive_thread(_build_state("u1", "t2"))
    archived = storage.load_archived("u1")
    assert len(archived) == 2
    assert archived[-1].thread_id == "t2"


def test_storage_is_utf8_json(tmp_path: Path) -> None:
    storage = ThreadStorage(storage_dir=tmp_path / "threads")
    storage.save_active(_build_state("u1", "t1"))
    raw = (tmp_path / "threads" / "u1_active.json").read_text(encoding="utf-8")
    payload = json.loads(raw)
    assert payload["thread_id"] == "t1"


def test_parallel_writes_do_not_crash(tmp_path: Path) -> None:
    storage = ThreadStorage(storage_dir=tmp_path / "threads")

    def _write(idx: int) -> None:
        storage.save_active(_build_state("u1", f"t{idx}"))

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(_write, range(20)))

    loaded = storage.load_active("u1")
    assert loaded is not None
    assert loaded.thread_id.startswith("t")

