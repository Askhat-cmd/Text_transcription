from __future__ import annotations

from datetime import datetime, timezone

from api.conversations.models import (
    ConversationContext,
    ConversationRecord,
    ConversationSummary,
    StartConversationRequest,
)


def test_conversation_models_serialize_datetime() -> None:
    now = datetime.now(timezone.utc)
    record = ConversationRecord(
        id="c1",
        user_id="u1",
        session_id="s1",
        channel="web",
        status="active",
        started_at=now,
        last_message_at=now,
    )
    payload = record.model_dump(mode="json")
    assert isinstance(payload["started_at"], str)
    assert isinstance(payload["last_message_at"], str)


def test_conversation_context_defaults() -> None:
    now = datetime.now(timezone.utc)
    ctx = ConversationContext(
        conversation_id="c2",
        user_id="u2",
        session_id="s2",
        channel="web",
        started_at=now,
    )
    assert ctx.status == "active"
    assert ctx.is_new is False


def test_start_request_and_summary() -> None:
    req = StartConversationRequest(title="Новый диалог")
    assert req.title == "Новый диалог"
    summary = ConversationSummary(
        conversation_id="c3",
        status="active",
        started_at=datetime.now(timezone.utc),
        last_message_at=datetime.now(timezone.utc),
    )
    assert summary.message_count == 0

