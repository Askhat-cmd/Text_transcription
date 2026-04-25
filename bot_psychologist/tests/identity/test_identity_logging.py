from __future__ import annotations

from pathlib import Path

import pytest

from api.identity.repository import IdentityRepository
from api.identity.service import IdentityService


@pytest.mark.asyncio
async def test_identity_logging_events(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    service = IdentityService(IdentityRepository(str(tmp_path / "identity.db")))
    caplog.set_level("INFO")

    await service.resolve_or_create(
        provider="web",
        external_id="sha256:log-1",
        session_id="s-1",
        channel="web",
    )
    await service.resolve_or_create(
        provider="web",
        external_id="sha256:log-1",
        session_id="s-2",
        channel="web",
    )

    messages = [rec.message for rec in caplog.records]
    assert any("identity.user_created" in msg for msg in messages)
    assert any("identity.user_resolved" in msg for msg in messages)
    assert any("identity.session_refreshed" in msg for msg in messages)

