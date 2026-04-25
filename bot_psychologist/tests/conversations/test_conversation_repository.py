from __future__ import annotations

import asyncio

import pytest

from api.conversations import ConversationRepository
from api.identity.repository import IdentityRepository


@pytest.mark.asyncio
async def test_create_conversation_returns_uuid(tmp_path) -> None:
    db_path = tmp_path / "conv_repo.db"
    identity_repo = IdentityRepository(str(db_path))
    user = identity_repo.create_user()
    session = identity_repo.upsert_session(session_id="s1", user_id=user.id, channel="web")
    repo = ConversationRepository(str(db_path))

    conv = await repo.create_conversation(user_id=user.id, session_id=session.session_id)
    assert len(conv.id) == 36
    assert conv.status == "active"


@pytest.mark.asyncio
async def test_get_active_conversation_returns_latest(tmp_path) -> None:
    db_path = tmp_path / "conv_repo.db"
    identity_repo = IdentityRepository(str(db_path))
    user = identity_repo.create_user()
    session = identity_repo.upsert_session(session_id="s2", user_id=user.id, channel="web")
    repo = ConversationRepository(str(db_path))

    conv_1 = await repo.create_conversation(user_id=user.id, session_id=session.session_id)
    await asyncio.sleep(0.01)
    conv_2 = await repo.create_conversation(user_id=user.id, session_id=session.session_id)
    active = await repo.get_active_conversation(user.id, session.session_id)

    assert active is not None
    assert active.id == conv_2.id
    assert active.id != conv_1.id


@pytest.mark.asyncio
async def test_get_active_conversation_returns_none_if_closed(tmp_path) -> None:
    db_path = tmp_path / "conv_repo.db"
    identity_repo = IdentityRepository(str(db_path))
    user = identity_repo.create_user()
    session = identity_repo.upsert_session(session_id="s3", user_id=user.id, channel="web")
    repo = ConversationRepository(str(db_path))

    conv = await repo.create_conversation(user_id=user.id, session_id=session.session_id)
    await repo.close_conversation(conv.id)
    result = await repo.get_active_conversation(user.id, session.session_id)
    assert result is None


@pytest.mark.asyncio
async def test_update_last_message_at(tmp_path) -> None:
    db_path = tmp_path / "conv_repo.db"
    identity_repo = IdentityRepository(str(db_path))
    user = identity_repo.create_user()
    session = identity_repo.upsert_session(session_id="s4", user_id=user.id, channel="web")
    repo = ConversationRepository(str(db_path))

    conv = await repo.create_conversation(user_id=user.id, session_id=session.session_id)
    old_ts = conv.last_message_at
    await asyncio.sleep(0.01)
    await repo.update_last_message_at(conv.id)
    updated = await repo.get_conversation(conv.id)
    assert updated is not None
    assert updated.last_message_at > old_ts


@pytest.mark.asyncio
async def test_list_user_conversations_pagination(tmp_path) -> None:
    db_path = tmp_path / "conv_repo.db"
    identity_repo = IdentityRepository(str(db_path))
    user = identity_repo.create_user()
    session = identity_repo.upsert_session(session_id="s5", user_id=user.id, channel="web")
    repo = ConversationRepository(str(db_path))

    for _ in range(5):
        await repo.create_conversation(user_id=user.id, session_id=session.session_id)

    listed = await repo.list_user_conversations(user.id, limit=3)
    assert len(listed) == 3


@pytest.mark.asyncio
async def test_archive_old_conversations(tmp_path) -> None:
    db_path = tmp_path / "conv_repo.db"
    identity_repo = IdentityRepository(str(db_path))
    user = identity_repo.create_user()
    session = identity_repo.upsert_session(session_id="s6", user_id=user.id, channel="web")
    repo = ConversationRepository(str(db_path))

    conv = await repo.create_conversation(user_id=user.id, session_id=session.session_id)
    await repo.close_conversation(conv.id)
    count = await repo.archive_old_conversations(user.id, days_threshold=0)
    assert count >= 1
    refreshed = await repo.get_conversation(conv.id)
    assert refreshed is not None
    assert refreshed.status == "archived"

