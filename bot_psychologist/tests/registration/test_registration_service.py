from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from api.identity import IdentityRepository, IdentityService
from api.registration.guards import LinkAttemptGuard
from api.registration.repository import RegistrationRepository
from api.registration.service import RegistrationService, RegistrationServiceError
from api.registration.security import verify_key


@pytest.mark.asyncio
async def test_service_register_and_login(registration_db_path) -> None:
    repo = RegistrationRepository(str(registration_db_path))
    identity_service = IdentityService(IdentityRepository(str(registration_db_path)))
    service = RegistrationService(
        repository=repo,
        identity_service=identity_service,
        link_guard=LinkAttemptGuard(),
    )

    repo.create_invite_key(
        key_value="BP-INVITE-1",
        role_grant="user",
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )

    registered = await service.register(username="user1", invite_key="BP-INVITE-1")
    profile = repo.get_profile_by_user_id(registered.user_id)
    assert profile is not None
    assert verify_key(registered.access_key, profile["hashed_access_key"]) is True

    login = await service.login(username="user1", access_key=registered.access_key)
    assert login.user_id == registered.user_id
    assert login.session_token


@pytest.mark.asyncio
async def test_service_confirm_link_code_flow(registration_db_path) -> None:
    repo = RegistrationRepository(str(registration_db_path))
    identity_service = IdentityService(IdentityRepository(str(registration_db_path)))
    service = RegistrationService(
        repository=repo,
        identity_service=identity_service,
        link_guard=LinkAttemptGuard(),
    )

    repo.create_invite_key(
        key_value="BP-INVITE-2",
        role_grant="user",
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )
    registered = await service.register(username="user2", invite_key="BP-INVITE-2")
    login = await service.login(username="user2", access_key=registered.access_key)
    link_code = await service.create_link_code(session_token=login.session_token)

    result = await service.confirm_telegram_link(code=link_code.code, telegram_user_id="777")
    assert result.ok is True
    assert result.user_id == registered.user_id


@pytest.mark.asyncio
async def test_service_rejects_wrong_credentials(registration_db_path) -> None:
    repo = RegistrationRepository(str(registration_db_path))
    identity_service = IdentityService(IdentityRepository(str(registration_db_path)))
    service = RegistrationService(
        repository=repo,
        identity_service=identity_service,
        link_guard=LinkAttemptGuard(),
    )

    repo.create_invite_key(
        key_value="BP-INVITE-3",
        role_grant="user",
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )
    await service.register(username="user3", invite_key="BP-INVITE-3")

    with pytest.raises(RegistrationServiceError):
        await service.login(username="user3", access_key="WRONG")
