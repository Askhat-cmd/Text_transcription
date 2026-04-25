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
    monkeypatch.setattr(config, "BOT_DB_PATH", tmp_path / "identity_stub.db", raising=False)
    monkeypatch.setattr(deps, "_identity_repository", None, raising=False)
    monkeypatch.setattr(deps, "_identity_service", None, raising=False)
    monkeypatch.setattr(deps, "_conversation_repository", None, raising=False)
    monkeypatch.setattr(deps, "_conversation_service", None, raising=False)
    with TestClient(app, base_url="http://localhost") as test_client:
        yield test_client


def test_generate_link_code_stub_returns_501(client: TestClient) -> None:
    res = client.get("/api/v1/identity/generate-link-code", headers={"X-API-Key": "test-key-001"})
    assert res.status_code == 501


def test_link_telegram_stub_returns_501(client: TestClient) -> None:
    res = client.post(
        "/api/v1/identity/link-telegram",
        headers={"X-API-Key": "test-key-001"},
        json={"code": "ABC123", "telegram_user_id": "123456789"},
    )
    assert res.status_code == 501
