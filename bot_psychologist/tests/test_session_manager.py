#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for SQLite SessionManager bootstrap from PRD v2.0."""

from datetime import datetime, timedelta, timezone

import numpy as np

from bot_agent.storage import SessionManager


def test_session_persistence() -> None:
    manager = SessionManager(db_path=":memory:")

    session_id = "test-session-1"
    manager.create_session(session_id=session_id, user_id="user_123")

    embedding = np.random.rand(16).astype(np.float32)
    manager.save_turn(
        session_id=session_id,
        turn_number=1,
        user_input="Мне тяжело",
        bot_response="Я рядом. Что сейчас самое трудное?",
        mode="PRESENCE",
        confidence=0.64,
        chunks_used=["эмоция", "контакт"],
        user_state="anxious",
        user_feedback="positive",
        user_rating=4,
        embedding=embedding,
    )
    manager.update_summary(session_id=session_id, summary="Пользователь описал тяжесть.")
    manager.update_working_state(
        session_id=session_id,
        working_state={"phase": "осмысление", "emotion": "тревога"},
    )

    payload = manager.load_session(session_id)
    assert payload is not None
    assert payload["session_info"]["user_id"] == "user_123"
    assert payload["session_info"]["conversation_summary"] == "Пользователь описал тяжесть."
    assert payload["session_info"]["working_state"]["phase"] == "осмысление"
    assert len(payload["conversation_turns"]) == 1
    assert payload["conversation_turns"][0]["mode"] == "PRESENCE"
    assert payload["conversation_turns"][0]["user_state"] == "anxious"
    assert payload["conversation_turns"][0]["user_feedback"] == "positive"
    assert payload["conversation_turns"][0]["user_rating"] == 4
    assert len(payload["semantic_embeddings"]) == 1
    assert payload["semantic_embeddings"][0]["embedding"].shape == (16,)


def test_session_archiving() -> None:
    manager = SessionManager(db_path=":memory:")
    session_id = "test-session-archive"
    manager.create_session(session_id=session_id, user_id="user_1")

    old_date = (datetime.now(timezone.utc) - timedelta(days=91)).isoformat()
    with manager._connect() as conn:  # noqa: SLF001 - тестовая подготовка
        conn.execute(
            "UPDATE sessions SET last_active = ? WHERE session_id = ?",
            (old_date, session_id),
        )

    archived = manager.archive_old_sessions(days=90)
    assert archived == 1

    payload = manager.load_session(session_id)
    assert payload is not None
    assert payload["session_info"]["status"] == "archived"


def test_retention_cleanup_deletes_old_archived() -> None:
    manager = SessionManager(db_path=":memory:")
    session_id = "test-session-old-archived"
    manager.create_session(session_id=session_id, user_id="user_2")

    old_date = (datetime.now(timezone.utc) - timedelta(days=500)).isoformat()
    with manager._connect() as conn:  # noqa: SLF001 - тестовая подготовка
        conn.execute(
            "UPDATE sessions SET status = 'archived', last_active = ? WHERE session_id = ?",
            (old_date, session_id),
        )

    result = manager.run_retention_cleanup(active_days=90, archive_days=365)
    assert result["deleted_count"] == 1
    assert manager.load_session(session_id) is None


def test_delete_session_data_cascades_turns_and_embeddings() -> None:
    manager = SessionManager(db_path=":memory:")
    session_id = "delete-cascade-session"
    manager.create_session(session_id=session_id, user_id="user_delete")

    embedding = np.random.rand(8).astype(np.float32)
    manager.save_turn(
        session_id=session_id,
        turn_number=1,
        user_input="first",
        bot_response="answer",
        mode="PRESENCE",
        embedding=embedding,
    )

    assert manager.load_session(session_id) is not None
    assert manager.delete_session_data(session_id) is True
    assert manager.load_session(session_id) is None

    with manager._connect() as conn:  # noqa: SLF001 - test-level DB assertion
        turns_count = conn.execute(
            "SELECT COUNT(*) FROM conversation_turns WHERE session_id = ?",
            (session_id,),
        ).fetchone()[0]
        embeddings_count = conn.execute(
            "SELECT COUNT(*) FROM semantic_embeddings WHERE session_id = ?",
            (session_id,),
        ).fetchone()[0]

    assert turns_count == 0
    assert embeddings_count == 0


def test_list_user_sessions_excludes_technical_identity_sessions() -> None:
    manager = SessionManager(db_path=":memory:")
    user_id = "user_for_sidebar"

    manager.create_session(
        session_id="sess_technical_1",
        user_id=user_id,
        metadata={"ip_hash": "ip_sha:abc", "channel": "web"},
    )
    manager.create_session(
        session_id="web_technical_2",
        user_id=user_id,
        metadata={"ip_hash": "ip_sha:def", "channel": "web"},
    )
    manager.create_session(session_id="legacy-visible-uuid", user_id=user_id, metadata={})
    manager.create_user_session(user_id=user_id, title="Visible chat")

    sessions = manager.list_user_sessions(user_id=user_id, limit=20)
    session_ids = {item["session_id"] for item in sessions}

    assert "sess_technical_1" not in session_ids
    assert "web_technical_2" not in session_ids
    assert "legacy-visible-uuid" in session_ids
