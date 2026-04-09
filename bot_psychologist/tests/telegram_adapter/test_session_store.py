from __future__ import annotations

from pathlib import Path

import pytest

from telegram_adapter.persistence import session_store


@pytest.fixture
def temp_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "test_sessions.db"
    monkeypatch.setenv("SESSION_DB_PATH", str(db_path))
    session_store._db_initialized_path = None
    yield db_path
    session_store._db_initialized_path = None


def test_t6_1_save_and_retrieve(temp_db: Path) -> None:
    session_store._save_session("user_123", "sess_abc")
    assert session_store._get_cached_session("user_123") == "sess_abc"


def test_t6_2_miss_returns_none(temp_db: Path) -> None:
    assert session_store._get_cached_session("unknown_user") is None


def test_t6_3_delete_session(temp_db: Path) -> None:
    session_store._save_session("user_del", "sess_del")
    session_store._delete_session("user_del")
    assert session_store._get_cached_session("user_del") is None


def test_t6_4_persists_across_connections(temp_db: Path) -> None:
    session_store._save_session("user_persist", "sess_persist")
    session_store._db_initialized_path = None  # emulate process restart
    assert session_store._get_cached_session("user_persist") == "sess_persist"

