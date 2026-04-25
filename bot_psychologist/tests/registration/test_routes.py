from __future__ import annotations

import hashlib
import hmac
import json
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
    db_path = tmp_path / "registration_routes.db"
    monkeypatch.setattr(config, "WARMUP_ON_START", False, raising=False)
    monkeypatch.setattr(config, "BOT_DB_PATH", db_path, raising=False)
    monkeypatch.setenv("DEV_API_KEY", "dev-key-001")
    monkeypatch.setenv("TEST_API_KEY", "test-key-001")
    monkeypatch.setenv("INTERNAL_TELEGRAM_KEY", "internal-telegram-key")

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


def _signature(payload: dict, secret: str) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).hexdigest()


def _seed_invite(key_value: str) -> None:
    repo = RegistrationRepository(str(config.BOT_DB_PATH))
    repo.create_invite_key(
        key_value=key_value,
        role_grant="user",
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )


def test_register_and_login_and_link_code_flow(client: TestClient) -> None:
    _seed_invite("INV-001")

    reg = client.post("/api/v1/auth/register", json={"username": "user1", "invite_key": "INV-001"})
    assert reg.status_code == 200
    reg_payload = reg.json()
    assert reg_payload["access_key"].startswith("BP-")

    login = client.post(
        "/api/v1/auth/login",
        json={"username": "user1", "access_key": reg_payload["access_key"]},
    )
    assert login.status_code == 200
    session_token = login.json()["session_token"]

    code_resp = client.post(
        "/api/v1/auth/telegram/link-code",
        headers={"Authorization": f"Bearer {session_token}"},
    )
    assert code_resp.status_code == 200
    code = code_resp.json()["code"]

    body = {"code": code, "telegram_user_id": "777"}
    confirm = client.post(
        "/api/v1/auth/telegram/confirm-link",
        json=body,
        headers={
            "X-Internal-Key": "internal-telegram-key",
            "X-Request-HMAC": _signature(body, "internal-telegram-key"),
        },
    )
    assert confirm.status_code == 200
    assert confirm.json()["ok"] is True


def test_confirm_link_requires_internal_headers(client: TestClient) -> None:
    body = {"code": "A1B2C3", "telegram_user_id": "777"}
    res = client.post("/api/v1/auth/telegram/confirm-link", json=body)
    assert res.status_code == 403


def test_admin_invite_requires_admin_session(client: TestClient) -> None:
    _seed_invite("INV-002")
    reg = client.post("/api/v1/auth/register", json={"username": "user2", "invite_key": "INV-002"})
    access_key = reg.json()["access_key"]
    login = client.post(
        "/api/v1/auth/login",
        json={"username": "user2", "access_key": access_key},
    )
    session_token = login.json()["session_token"]

    invite = client.post(
        "/api/v1/admin/invite-keys",
        headers={"Authorization": f"Bearer {session_token}"},
        json={"role_grant": "user", "expires_in_days": 7},
    )
    assert invite.status_code == 403
