from __future__ import annotations

import importlib
import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

thread_storage_module = importlib.import_module("bot_agent.multiagent.thread_storage")
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.thread_storage import ThreadStorage


def _state(user_id: str, thread_id: str) -> ThreadState:
    now = datetime.utcnow()
    return ThreadState(
        thread_id=thread_id,
        user_id=user_id,
        core_direction="continuity-check",
        phase="clarify",
        created_at=now,
        updated_at=now,
    )


def test_ts_01_save_then_load_same_instance(tmp_path: Path) -> None:
    storage = ThreadStorage(storage_dir=tmp_path / "threads")
    storage.save_active(_state("u-ts-1", "thread-1"))
    loaded = storage.load_active("u-ts-1")
    assert loaded is not None
    assert loaded.thread_id == "thread-1"


def test_ts_02_save_then_load_new_instance(tmp_path: Path) -> None:
    storage_1 = ThreadStorage(storage_dir=tmp_path / "threads")
    storage_1.save_active(_state("u-ts-2", "thread-2"))

    storage_2 = ThreadStorage(storage_dir=tmp_path / "threads")
    loaded = storage_2.load_active("u-ts-2")
    assert loaded is not None
    assert loaded.thread_id == "thread-2"


def test_ts_03_path_is_absolute(tmp_path: Path) -> None:
    storage = ThreadStorage(storage_dir=tmp_path / "threads")
    assert storage._dir.is_absolute() is True


def test_ts_04_path_consistent_from_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_path = tmp_path / "env_threads"
    monkeypatch.setenv("THREAD_STORAGE_DIR", str(env_path))

    reloaded = importlib.reload(thread_storage_module)
    try:
        storage = reloaded.ThreadStorage()
        assert storage._dir == env_path.resolve()
    finally:
        monkeypatch.delenv("THREAD_STORAGE_DIR", raising=False)
        importlib.reload(thread_storage_module)


def test_ts_05_continuity_scenario(tmp_path: Path) -> None:
    user_id = "live_test_001"
    saved_thread_id = "continuity-thread-001"

    writer = ThreadStorage(storage_dir=tmp_path / "threads")
    writer.save_active(_state(user_id, saved_thread_id))

    reader = ThreadStorage(storage_dir=tmp_path / "threads")
    loaded = reader.load_active(user_id)
    assert loaded is not None
    assert loaded.thread_id == saved_thread_id
