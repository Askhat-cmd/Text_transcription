from __future__ import annotations

from pathlib import Path

import pytest

from api.conversations import ConversationRepository, ConversationService
from api.identity.repository import IdentityRepository


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "conversations.db"


@pytest.fixture()
def identity_repo(db_path: Path) -> IdentityRepository:
    return IdentityRepository(str(db_path))


@pytest.fixture()
def conversation_repo(db_path: Path) -> ConversationRepository:
    return ConversationRepository(str(db_path))


@pytest.fixture()
def conversation_service(conversation_repo: ConversationRepository) -> ConversationService:
    return ConversationService(conversation_repo)


@pytest.fixture()
def user_session(identity_repo: IdentityRepository) -> tuple[str, str]:
    user = identity_repo.create_user()
    session = identity_repo.upsert_session(
        session_id="sess-test-1",
        user_id=user.id,
        channel="web",
        device_fingerprint="sha256:test-user",
    )
    return user.id, session.session_id

