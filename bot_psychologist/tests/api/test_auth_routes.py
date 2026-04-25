from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api import dependencies as deps
from api.main import app
from api.registration.repository import RegistrationRepository
from bot_agent.config import config


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "auth_routes.db"
    monkeypatch.setattr(config, "WARMUP_ON_START", False, raising=False)
    monkeypatch.setattr(config, "BOT_DB_PATH", db_path, raising=False)

    for attr in [
        "_identity_repository",
        "_identity_service",
        "_conversation_repository",
        "_conversation_service",
        "_registration_repository",
        "_registration_service",
        "_link_attempt_guard",
        "_database_bootstrap",
        "_telegram_adapter_service",
        "_telegram_outbound_sender",
    ]:
        monkeypatch.setattr(deps, attr, None, raising=False)

    with TestClient(app, base_url="http://localhost") as test_client:
        yield test_client


def test_register_and_login_endpoints(client: TestClient) -> None:
    repo = RegistrationRepository(str(config.BOT_DB_PATH))
    repo.create_invite_key(
        key_value="INV-ENDPOINT",
        role_grant="user",
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )

    reg = client.post(
        "/api/v1/auth/register",
        json={"username": "endpoint_user", "invite_key": "INV-ENDPOINT"},
    )
    assert reg.status_code == 200
    access_key = reg.json()["access_key"]

    login = client.post(
        "/api/v1/auth/login",
        json={"username": "endpoint_user", "access_key": access_key},
    )
    assert login.status_code == 200
    assert "session_token" in login.json()


def test_link_code_requires_session(client: TestClient) -> None:
    res = client.post("/api/v1/auth/telegram/link-code")
    assert res.status_code == 401
