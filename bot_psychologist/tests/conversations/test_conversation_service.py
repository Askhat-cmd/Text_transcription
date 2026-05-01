from __future__ import annotations

import asyncio
import logging

import pytest

from api.conversations import ConversationRepository, ConversationService
from api.identity.repository import IdentityRepository


@pytest.fixture()
def prepared_service(tmp_path):
    db_path = tmp_path / "conv_service.db"
    identity_repo = IdentityRepository(str(db_path))
    user = identity_repo.create_user()
    session = identity_repo.upsert_session(session_id="srv-s1", user_id=user.id, channel="web")
    service = ConversationService(ConversationRepository(str(db_path)))
    return service, user.id, session.session_id


@pytest.mark.asyncio
async def test_get_or_create_creates_new_on_first_call(prepared_service) -> None:
    service, user_id, session_id = prepared_service
    ctx = await service.get_or_create_conversation(user_id=user_id, session_id=session_id)
    assert ctx.is_new is True
    assert ctx.status == "active"


@pytest.mark.asyncio
async def test_get_or_create_returns_existing(prepared_service) -> None:
    service, user_id, session_id = prepared_service
    ctx1 = await service.get_or_create_conversation(user_id=user_id, session_id=session_id)
    await asyncio.sleep(0.01)
    ctx2 = await service.get_or_create_conversation(user_id=user_id, session_id=session_id)
    assert ctx1.conversation_id == ctx2.conversation_id
    assert ctx2.is_new is False


@pytest.mark.asyncio
async def test_start_new_pauses_previous(prepared_service) -> None:
    service, user_id, session_id = prepared_service
    repo = service._repo  # noqa: SLF001 - test verification
    first = await service.get_or_create_conversation(user_id=user_id, session_id=session_id)
    second = await service.start_new_conversation(user_id=user_id, session_id=session_id)
    assert first.conversation_id != second.conversation_id
    prev = await repo.get_conversation(first.conversation_id)
    assert prev is not None
    assert prev.status == "paused"


@pytest.mark.asyncio
async def test_close_conversation_checks_ownership(prepared_service) -> None:
    service, user_id, session_id = prepared_service
    ctx = await service.get_or_create_conversation(user_id=user_id, session_id=session_id)
    with pytest.raises(PermissionError):
        await service.close_conversation(ctx.conversation_id, user_id="u2")


@pytest.mark.asyncio
async def test_touch_updates_last_message_at(prepared_service) -> None:
    service, user_id, session_id = prepared_service
    repo = service._repo  # noqa: SLF001 - test verification
    ctx = await service.get_or_create_conversation(user_id=user_id, session_id=session_id)
    before = await repo.get_conversation(ctx.conversation_id)
    await asyncio.sleep(0.01)
    await service.touch_conversation(ctx.conversation_id)
    after = await repo.get_conversation(ctx.conversation_id)
    assert before is not None and after is not None
    assert after.last_message_at > before.last_message_at


@pytest.mark.asyncio
async def test_get_or_create_logs_lookup_user_fallback(prepared_service, caplog) -> None:
    service, user_id, session_id = prepared_service
    repo = service._repo  # noqa: SLF001 - test verification
    caplog.set_level(logging.INFO, logger="api.conversations.service")

    first = await service.get_or_create_conversation(user_id=user_id, session_id=session_id)

    identity_repo = IdentityRepository(repo._db_path)  # noqa: SLF001 - test wiring
    other_session = identity_repo.upsert_session(
        session_id="srv-s1-alt",
        user_id=user_id,
        channel="web",
    )
    resumed = await service.get_or_create_conversation(
        user_id=user_id,
        session_id=other_session.session_id,
    )

    assert resumed.conversation_id == first.conversation_id
    resume_logs = [r for r in caplog.records if r.msg == "conversation.resumed"]
    assert resume_logs
    assert getattr(resume_logs[-1], "lookup", None) == "user_fallback"


@pytest.mark.asyncio
async def test_get_or_create_logs_create_reason(prepared_service, caplog) -> None:
    service, user_id, session_id = prepared_service
    caplog.set_level(logging.INFO, logger="api.conversations.service")

    created = await service.get_or_create_conversation(user_id=user_id, session_id=session_id)
    assert created.is_new is True

    create_logs = [r for r in caplog.records if r.msg == "conversation.created"]
    assert create_logs
    assert getattr(create_logs[-1], "reason", None) == "no_active_found"
