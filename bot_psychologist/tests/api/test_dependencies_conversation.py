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
    monkeypatch.setattr(config, "BOT_DB_PATH", tmp_path / "identity_conv_dep.db", raising=False)
    monkeypatch.setattr(deps, "_identity_repository", None, raising=False)
    monkeypatch.setattr(deps, "_identity_service", None, raising=False)
    monkeypatch.setattr(deps, "_conversation_repository", None, raising=False)
    monkeypatch.setattr(deps, "_conversation_service", None, raising=False)
    with TestClient(app, base_url="http://localhost") as test_client:
        yield test_client


def _headers(session_id: str, fingerprint: str) -> dict[str, str]:
    return {
        "X-API-Key": "test-key-001",
        "X-Session-Id": session_id,
        "X-Device-Fingerprint": fingerprint,
    }


def test_identity_context_uses_real_conversation_id(client: TestClient) -> None:
    headers = _headers("dep-s1", "sha256:dep-fp-1")
    first = client.get("/api/v1/identity/me", headers=headers)
    assert first.status_code == 200
    payload = first.json()
    assert payload["conversation_id"]
    assert payload["conversation_id"] != payload["session_id"]


def test_conversation_header_restores_same_conversation(client: TestClient) -> None:
    headers = _headers("dep-s2", "sha256:dep-fp-2")
    first = client.get("/api/v1/identity/me", headers=headers)
    conv_id = first.json()["conversation_id"]

    second_headers = dict(headers)
    second_headers["X-Conversation-Id"] = conv_id
    second = client.get("/api/v1/identity/me", headers=second_headers)
    assert second.status_code == 200
    assert second.json()["conversation_id"] == conv_id


def test_foreign_conversation_header_is_ignored(client: TestClient) -> None:
    user_a = _headers("dep-a", "sha256:dep-fp-a")
    user_b = _headers("dep-b", "sha256:dep-fp-b")

    conv_a = client.get("/api/v1/identity/me", headers=user_a).json()["conversation_id"]
    first_b = client.get("/api/v1/identity/me", headers=user_b).json()["conversation_id"]

    forced_b = dict(user_b)
    forced_b["X-Conversation-Id"] = conv_a
    second_b = client.get("/api/v1/identity/me", headers=forced_b).json()["conversation_id"]

    assert first_b != conv_a
    assert second_b != conv_a

