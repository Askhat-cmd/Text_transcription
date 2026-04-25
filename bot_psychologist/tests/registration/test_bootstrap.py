from __future__ import annotations

from api.identity import IdentityRepository, IdentityService
from api.registration.bootstrap import DatabaseBootstrap
from api.registration.repository import RegistrationRepository


import pytest


@pytest.mark.asyncio
async def test_bootstrap_creates_api_keys(registration_db_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEV_API_KEY", "dev-key-001")
    monkeypatch.setenv("TEST_API_KEY", "test-key-001")
    monkeypatch.setenv("INTERNAL_TELEGRAM_KEY", "internal-telegram-key")

    repo = RegistrationRepository(str(registration_db_path))
    identity_service = IdentityService(IdentityRepository(str(registration_db_path)))
    bootstrap = DatabaseBootstrap(repository=repo, identity_service=identity_service)

    await bootstrap.run()
    assert repo.get_api_key("dev-key-001") is not None
    assert repo.get_api_key("test-key-001") is not None


@pytest.mark.asyncio
async def test_bootstrap_is_idempotent(registration_db_path) -> None:
    repo = RegistrationRepository(str(registration_db_path))
    identity_service = IdentityService(IdentityRepository(str(registration_db_path)))
    bootstrap = DatabaseBootstrap(repository=repo, identity_service=identity_service)

    await bootstrap.run()
    await bootstrap.run()
    keys = repo.list_api_keys()
    assert len(keys) >= 2
