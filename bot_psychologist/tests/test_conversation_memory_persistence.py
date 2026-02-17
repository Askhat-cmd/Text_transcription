#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Integration tests for ConversationMemory + SQLite session restore."""

from pathlib import Path

from bot_agent.config import config
from bot_agent.conversation_memory import ConversationMemory
from bot_agent.working_state import WorkingState


def test_conversation_memory_prefers_sqlite_over_json(monkeypatch, tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

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


def test_conversation_memory_gdpr_purge(monkeypatch, tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

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
