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
    monkeypatch.setattr(config, "BOT_DB_PATH", tmp_path / "conversation_routes.db", raising=False)
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


def test_list_conversations_returns_user_scope(client: TestClient) -> None:
    headers_a = _headers("conv-routes-a", "sha256:conv-routes-a")
    headers_b = _headers("conv-routes-b", "sha256:conv-routes-b")

    client.post("/api/v1/conversations/new", headers=headers_a, json={"title": "A1"})
    client.post("/api/v1/conversations/new", headers=headers_b, json={"title": "B1"})

    res_a = client.get("/api/v1/conversations/", headers=headers_a)
    res_b = client.get("/api/v1/conversations/", headers=headers_b)

    assert res_a.status_code == 200
    assert res_b.status_code == 200
    assert all(item["conversation_id"] for item in res_a.json())
    assert all(item["conversation_id"] for item in res_b.json())
    assert {item["conversation_id"] for item in res_a.json()} != {
        item["conversation_id"] for item in res_b.json()
    }


def test_start_new_conversation_returns_context(client: TestClient) -> None:
    headers = _headers("conv-routes-c", "sha256:conv-routes-c")
    res = client.post("/api/v1/conversations/new", headers=headers, json={"title": "Новый"})
    assert res.status_code == 200
    payload = res.json()
    assert payload["conversation_id"]
    assert payload["is_new"] is True


def test_close_conversation_rejects_foreign_owner(client: TestClient) -> None:
    owner_headers = _headers("conv-routes-owner", "sha256:conv-owner")
    foreign_headers = _headers("conv-routes-foreign", "sha256:conv-foreign")

    created = client.post("/api/v1/conversations/new", headers=owner_headers, json={})
    conv_id = created.json()["conversation_id"]

    res = client.post(f"/api/v1/conversations/{conv_id}/close", headers=foreign_headers)
    assert res.status_code == 403

