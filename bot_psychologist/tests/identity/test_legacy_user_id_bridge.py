from __future__ import annotations

from pathlib import Path

import pytest

from api.identity.repository import IdentityRepository
from api.identity.service import IdentityService


@pytest.fixture()
def service(tmp_path: Path) -> IdentityService:
    return IdentityService(IdentityRepository(str(tmp_path / "identity.db")))


@pytest.mark.asyncio
async def test_legacy_user_id_is_preserved(service: IdentityService) -> None:
    first = await service.resolve_or_create(
        provider="web",
        external_id="sha256:legacy-a",
        session_id="s-1",
        legacy_user_id="legacy_user_42",
    )
    second = await service.resolve_or_create(
        provider="web",
        external_id="sha256:legacy-b",
        session_id="s-2",
        legacy_user_id="legacy_user_42",
    )
    assert first.user_id == second.user_id


@pytest.mark.asyncio
async def test_no_duplicate_on_repeated_legacy_calls(service: IdentityService) -> None:
    user_ids: set[str] = set()
    for idx in range(3):
        ctx = await service.resolve_or_create(
            provider="web",
            external_id=f"sha256:legacy-{idx}",
            session_id=f"s-{idx}",
            legacy_user_id="legacy_repeat",
        )
        user_ids.add(ctx.user_id)
    assert len(user_ids) == 1


@pytest.mark.asyncio
async def test_legacy_warn_is_logged(service: IdentityService, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level("WARNING")
    await service.resolve_or_create(
        provider="web",
        external_id="sha256:legacy-log",
        session_id="s-log",
        legacy_user_id="legacy_warn_id",
    )
    assert any("identity.legacy_user_id_used" in rec.message for rec in caplog.records)

