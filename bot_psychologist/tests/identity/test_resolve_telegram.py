from __future__ import annotations

from pathlib import Path

import pytest

from api.identity.repository import IdentityRepository
from api.identity.service import IdentityService


@pytest.fixture()
def service(tmp_path: Path) -> IdentityService:
    return IdentityService(IdentityRepository(str(tmp_path / "identity.db")))


@pytest.mark.asyncio
async def test_resolve_telegram_returns_none_when_not_linked(service: IdentityService) -> None:
    resolved = await service.resolve_telegram("123456")
    assert resolved is None


@pytest.mark.asyncio
async def test_resolve_telegram_returns_existing_user(service: IdentityService) -> None:
    ctx = await service.resolve_or_create(
        provider="web",
        external_id="sha256:tg-owner",
        session_id="s-1",
        channel="web",
    )
    await service.link_identity(
        user_id=ctx.user_id,
        provider="telegram",
        external_id="777888",
    )
    resolved = await service.resolve_telegram("777888")
    assert resolved is not None
    assert resolved.user_id == ctx.user_id
    assert resolved.provider == "telegram"

