from __future__ import annotations

from pathlib import Path

import pytest

from api.identity.repository import IdentityRepository
from api.identity.service import IdentityService


@pytest.fixture()
def service(tmp_path: Path) -> IdentityService:
    repo = IdentityRepository(str(tmp_path / "identity.db"))
    return IdentityService(repo)


@pytest.mark.asyncio
async def test_resolve_creates_new_user_on_first_call(service: IdentityService) -> None:
    ctx = await service.resolve_or_create(
        provider="web",
        external_id="sha256:first",
        session_id="s-1",
        channel="web",
    )
    assert ctx.created_new_user is True
    assert ctx.user_id


@pytest.mark.asyncio
async def test_resolve_returns_same_user_on_second_call(service: IdentityService) -> None:
    ctx1 = await service.resolve_or_create(
        provider="web",
        external_id="sha256:sticky",
        session_id="s-1",
        channel="web",
    )
    ctx2 = await service.resolve_or_create(
        provider="web",
        external_id="sha256:sticky",
        session_id="s-2",
        channel="web",
    )
    assert ctx1.user_id == ctx2.user_id
    assert ctx2.created_new_user is False


@pytest.mark.asyncio
async def test_resolve_created_new_user_flag(service: IdentityService) -> None:
    first = await service.resolve_or_create(
        provider="web",
        external_id="sha256:new-flag",
        session_id="s-1",
        channel="web",
    )
    second = await service.resolve_or_create(
        provider="web",
        external_id="sha256:new-flag",
        session_id="s-2",
        channel="web",
    )
    assert first.created_new_user is True
    assert second.created_new_user is False


@pytest.mark.asyncio
async def test_link_identity_adds_second_provider(service: IdentityService) -> None:
    ctx = await service.resolve_or_create(
        provider="web",
        external_id="sha256:link-me",
        session_id="s-1",
        channel="web",
    )
    await service.link_identity(
        user_id=ctx.user_id,
        provider="telegram",
        external_id="123456",
    )
    linked = await service.get_linked_identities(ctx.user_id)
    providers = {item.provider for item in linked}
    assert {"web", "telegram"} <= providers


@pytest.mark.asyncio
async def test_link_identity_does_not_duplicate(service: IdentityService) -> None:
    ctx = await service.resolve_or_create(
        provider="web",
        external_id="sha256:no-dup",
        session_id="s-1",
        channel="web",
    )
    await service.link_identity(
        user_id=ctx.user_id,
        provider="telegram",
        external_id="222",
    )
    await service.link_identity(
        user_id=ctx.user_id,
        provider="telegram",
        external_id="222",
    )
    linked = await service.get_linked_identities(ctx.user_id)
    tg_ids = [item.external_id for item in linked if item.provider == "telegram"]
    assert tg_ids.count("222") == 1


@pytest.mark.asyncio
async def test_resolve_returns_existing_after_link(service: IdentityService) -> None:
    ctx = await service.resolve_or_create(
        provider="web",
        external_id="sha256:bridge",
        session_id="s-1",
        channel="web",
    )
    await service.link_identity(
        user_id=ctx.user_id,
        provider="telegram",
        external_id="999999",
    )
    tg = await service.resolve_telegram("999999")
    assert tg is not None
    assert tg.user_id == ctx.user_id
    assert tg.provider == "telegram"

