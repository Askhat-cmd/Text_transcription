#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Integration tests for ConversationMemory + SQLite session restore."""

import shutil
import sqlite3
import uuid
from pathlib import Path

import pytest

from bot_agent.config import config
from bot_agent.conversation_memory import ConversationMemory
from bot_agent.working_state import WorkingState


_LOCAL_TMP_ROOT = Path(__file__).resolve().parent / "_tmp_memory_persistence"


def _sqlite_disk_available() -> bool:
    probe_root = _LOCAL_TMP_ROOT / "_sqlite_probe"
    probe_root.mkdir(parents=True, exist_ok=True)
    probe_db = probe_root / "probe.db"
    try:
        conn = sqlite3.connect(probe_db)
        conn.execute("CREATE TABLE IF NOT EXISTS t(x INTEGER)")
        conn.execute("INSERT INTO t VALUES (1)")
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False
    finally:
        shutil.rmtree(probe_root, ignore_errors=True)


pytestmark = pytest.mark.skipif(
    not _sqlite_disk_available(),
    reason="SQLite disk writes are unavailable in this environment (WinError 5 / disk I/O).",
)


def _new_tmp_path() -> Path:
    path = _LOCAL_TMP_ROOT / uuid.uuid4().hex
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_conversation_memory_prefers_sqlite_over_json(monkeypatch) -> None:
    tmp_path = _new_tmp_path()
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    try:
        monkeypatch.setattr(config, "CACHE_DIR", cache_dir)
        monkeypatch.setattr(config, "ENABLE_SEMANTIC_MEMORY", False)
        monkeypatch.setattr(config, "ENABLE_CONVERSATION_SUMMARY", False)
        monkeypatch.setattr(config, "ENABLE_SESSION_STORAGE", True)
        monkeypatch.setattr(config, "BOT_DB_PATH", tmp_path / "bot_sessions.db")

        user_id = "sqlite_preferred_user"

        writer = ConversationMemory(user_id=user_id)
        writer.set_working_state(
            WorkingState(
                dominant_state="фрустрация",
                emotion="тревога",
                phase="осмысление",
                direction="диагностика",
                confidence_level="medium",
            )
        )
        writer.add_turn(
            user_input="Мне трудно начать действовать",
            bot_response="Слышу, что застревание тяжёлое. Что именно останавливает?",
            user_state="stuck",
            concepts=["действие", "застревание"],
        )
        writer.add_feedback(turn_index=0, feedback="positive", rating=5)

        # Ломаем JSON-файл: загрузка должна пройти через SQLite.
        json_path = writer.memory_dir / f"{user_id}.json"
        json_path.write_text("{broken-json", encoding="utf-8")

        reader = ConversationMemory(user_id=user_id)
        loaded = reader.load_from_disk()

        assert loaded is True
        assert len(reader.turns) == 1
        assert reader.turns[0].user_input == "Мне трудно начать действовать"
        assert reader.turns[0].bot_response == "Слышу, что застревание тяжёлое. Что именно останавливает?"
        assert reader.turns[0].user_state == "stuck"
        assert reader.turns[0].user_feedback == "positive"
        assert reader.turns[0].user_rating == 5
        assert reader.working_state is not None
        assert reader.working_state.phase == "осмысление"
        assert reader.working_state.get_user_stage() == "awareness"
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_conversation_memory_gdpr_purge(monkeypatch) -> None:
    tmp_path = _new_tmp_path()
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    try:
        monkeypatch.setattr(config, "CACHE_DIR", cache_dir)
        monkeypatch.setattr(config, "ENABLE_SEMANTIC_MEMORY", False)
        monkeypatch.setattr(config, "ENABLE_CONVERSATION_SUMMARY", False)
        monkeypatch.setattr(config, "ENABLE_SESSION_STORAGE", True)
        monkeypatch.setattr(config, "BOT_DB_PATH", tmp_path / "bot_sessions.db")

        user_id = "gdpr_purge_user"
        memory = ConversationMemory(user_id=user_id)
        memory.add_turn(
            user_input="Хочу удалить все данные",
            bot_response="Понял, можем это сделать.",
        )

        json_path = memory.memory_dir / f"{user_id}.json"
        assert json_path.exists()
        assert memory.session_manager is not None
        assert memory.session_manager.load_session(user_id) is not None

        memory.purge_user_data()

        assert not json_path.exists()
        assert memory.session_manager.load_session(user_id) is None
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_load_cross_session_context_returns_empty_for_first_session(monkeypatch) -> None:
    tmp_path = _new_tmp_path()
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    try:
        monkeypatch.setattr(config, "CACHE_DIR", cache_dir)
        monkeypatch.setattr(config, "ENABLE_SEMANTIC_MEMORY", False)
        monkeypatch.setattr(config, "ENABLE_CONVERSATION_SUMMARY", False)
        monkeypatch.setattr(config, "ENABLE_SESSION_STORAGE", True)
        monkeypatch.setattr(config, "BOT_DB_PATH", tmp_path / "bot_sessions.db")

        memory = ConversationMemory(user_id="session_first")
        context = memory.load_cross_session_context(user_id="user_alpha", limit=3)
        assert context == ""
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_cross_session_context_reads_recent_summaries(monkeypatch) -> None:
    tmp_path = _new_tmp_path()
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    try:
        monkeypatch.setattr(config, "CACHE_DIR", cache_dir)
        monkeypatch.setattr(config, "ENABLE_SEMANTIC_MEMORY", False)
        monkeypatch.setattr(config, "ENABLE_CONVERSATION_SUMMARY", False)
        monkeypatch.setattr(config, "ENABLE_SESSION_STORAGE", True)
        monkeypatch.setattr(config, "BOT_DB_PATH", tmp_path / "bot_sessions.db")

        owner_user_id = "user_cross"
        memory_a = ConversationMemory(user_id="session_a")
        memory_a.save_session_summary(
            user_id=owner_user_id,
            summary={
                "session_id": "session_a",
                "date": "2026-03-28",
                "key_themes": ["избегание", "вина"],
                "sd_level_end": "BLUE",
                "state_end": "curious",
                "notable_moments": ["Пользователь увидел триггер избегания"],
            },
        )

        memory_b = ConversationMemory(user_id="session_b")
        memory_b.save_session_summary(
            user_id=owner_user_id,
            summary={
                "session_id": "session_b",
                "date": "2026-03-29",
                "key_themes": ["самооценка", "границы"],
                "sd_level_end": "GREEN",
                "state_end": "integrated",
                "notable_moments": ["Зафиксирован рабочий шаг"],
            },
        )

        context = memory_b.load_cross_session_context(user_id=owner_user_id, limit=3)
        assert "Из предыдущих сессий" in context
        assert "самооценка" in context
        assert "избегание" in context
        assert "состояние: integrated" in context
        assert "SD:" not in context
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)
