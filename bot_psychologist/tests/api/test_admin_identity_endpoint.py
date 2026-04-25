from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api import dependencies as deps
from api.main import app
from bot_agent.config import config


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "WARMUP_ON_START", False, raising=False)
    monkeypatch.setattr(config, "BOT_DB_PATH", tmp_path / "identity_admin.db", raising=False)
    monkeypatch.setattr(deps, "_identity_repository", None, raising=False)
    monkeypatch.setattr(deps, "_identity_service", None, raising=False)
    monkeypatch.setattr(deps, "_conversation_repository", None, raising=False)
    monkeypatch.setattr(deps, "_conversation_service", None, raising=False)
    with TestClient(app, base_url="http://localhost") as test_client:
        yield test_client


@pytest.mark.asyncio
async def test_admin_identity_requires_dev_key(client: TestClient) -> None:
    res = client.get(
        "/api/v1/admin/users/some-user/identity",
        headers={"X-API-Key": "test-key-001"},
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_admin_identity_returns_linked_identities(client: TestClient) -> None:
    service = deps.get_identity_service()
    ctx = await service.resolve_or_create(
        provider="web",
        external_id="sha256:abcdef0123456789",
        session_id="admin-session",
    )
    await service.link_identity(user_id=ctx.user_id, provider="telegram", external_id="123456789")

    res = client.get(
        f"/api/v1/admin/users/{ctx.user_id}/identity",
        headers={"X-API-Key": "dev-key-001"},
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload["user_id"] == ctx.user_id
    assert isinstance(payload["linked_identities"], list)
    assert isinstance(payload["active_sessions"], list)


@pytest.mark.asyncio
async def test_admin_identity_hides_full_fingerprint(client: TestClient) -> None:
    service = deps.get_identity_service()
    ctx = await service.resolve_or_create(
        provider="web",
        external_id="sha256:1234567890abcdef",
        session_id="mask-session",
    )
    res = client.get(
        f"/api/v1/admin/users/{ctx.user_id}/identity",
        headers={"X-API-Key": "dev-key-001"},
    )
    assert res.status_code == 200
    linked = res.json().get("linked_identities", [])
    web_rows = [row for row in linked if row.get("provider") == "web"]
    assert web_rows, "web linked identity is expected"
    masked = web_rows[0]["external_id"]
    assert masked.startswith("sha256:")
    assert masked.endswith("...")
    assert masked != "sha256:1234567890abcdef"
