from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

import api.routes as routes
from api import dependencies as deps
from api.main import app
from bot_agent.config import config


def _stub_adaptive_result(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
    return {
        "status": "success",
        "answer": "stub answer",
        "state_analysis": {
            "primary_state": "curious",
            "confidence": 0.8,
            "emotional_tone": "neutral",
            "recommendations": [],
        },
        "path_recommendation": None,
        "feedback_prompt": "stub feedback",
        "concepts": [],
        "sources": [],
        "conversation_context": "",
        "metadata": {},
        "processing_time_seconds": 0.01,
    }


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "WARMUP_ON_START", False, raising=False)
    monkeypatch.setattr(config, "BOT_DB_PATH", tmp_path / "identity_api.db", raising=False)
    monkeypatch.setattr(deps, "_identity_repository", None, raising=False)
    monkeypatch.setattr(deps, "_identity_service", None, raising=False)
    monkeypatch.setattr(deps, "_conversation_repository", None, raising=False)
    monkeypatch.setattr(deps, "_conversation_service", None, raising=False)
    monkeypatch.setattr(routes, "run_multiagent_adaptive_sync", _stub_adaptive_result, raising=True)
    with TestClient(app, base_url="http://localhost") as test_client:
        yield test_client


def test_ask_without_headers_succeeds(client: TestClient) -> None:
    res = client.post(
        "/api/v1/questions/adaptive",
        headers={"X-API-Key": "test-key-001"},
        json={"query": "Привет, тест"},
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload["status"] == "success"
    assert payload["answer"] == "stub answer"


def test_ask_with_fingerprint_header_creates_user(client: TestClient) -> None:
    headers = {
        "X-API-Key": "test-key-001",
        "X-Device-Fingerprint": "sha256:explicit-fp",
        "X-Session-Id": "session-fp-1",
    }
    res = client.post("/api/v1/questions/adaptive", headers=headers, json={"query": "Q11"})
    assert res.status_code == 200

    me = client.get("/api/v1/identity/me", headers=headers)
    assert me.status_code == 200
    payload = me.json()
    assert payload["user_id"]
    assert payload["session_id"] == "session-fp-1"
    assert payload["external_id"].startswith("sha256:")
    assert payload["external_id"].endswith("...")
    assert payload["external_id"] != "sha256:explicit-fp"


def test_ask_same_fingerprint_uses_same_user(client: TestClient) -> None:
    headers_1 = {
        "X-API-Key": "test-key-001",
        "X-Device-Fingerprint": "sha256:same-fp",
        "X-Session-Id": "session-a",
    }
    headers_2 = {
        "X-API-Key": "test-key-001",
        "X-Device-Fingerprint": "sha256:same-fp",
        "X-Session-Id": "session-b",
    }
    client.post("/api/v1/questions/adaptive", headers=headers_1, json={"query": "Q11"})
    client.post("/api/v1/questions/adaptive", headers=headers_2, json={"query": "Q22"})
    user_a = client.get("/api/v1/identity/me", headers=headers_1).json()["user_id"]
    user_b = client.get("/api/v1/identity/me", headers=headers_2).json()["user_id"]
    assert user_a == user_b


def test_ask_legacy_user_id_still_works(client: TestClient) -> None:
    res = client.post(
        "/api/v1/questions/adaptive",
        headers={"X-API-Key": "test-key-001"},
        json={"query": "legacy", "user_id": "legacy_user_123"},
    )
    assert res.status_code == 200


def test_history_scoped_to_user(client: TestClient) -> None:
    h1 = {
        "X-API-Key": "test-key-001",
        "X-Device-Fingerprint": "sha256:scoped-1",
        "X-Session-Id": "scoped-s1",
    }
    h2 = {
        "X-API-Key": "test-key-001",
        "X-Device-Fingerprint": "sha256:scoped-2",
        "X-Session-Id": "scoped-s2",
    }

    client.post("/api/v1/questions/adaptive", headers=h1, json={"query": "A"})
    client.post("/api/v1/questions/adaptive", headers=h2, json={"query": "B"})

    r1 = client.post("/api/v1/users/ignored/history", headers=h1, params={"last_n_turns": 5})
    r2 = client.post("/api/v1/users/ignored/history", headers=h2, params={"last_n_turns": 5})
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["user_id"] != r2.json()["user_id"]


def test_identity_session_metadata_uses_ip_hash(tmp_path: Path, client: TestClient) -> None:
    headers = {
        "X-API-Key": "test-key-001",
        "X-Device-Fingerprint": "sha256:meta-fp",
        "X-Session-Id": "meta-session",
        "X-Forwarded-For": "203.0.113.7",
    }
    me = client.get("/api/v1/identity/me", headers=headers)
    assert me.status_code == 200

    db_path = tmp_path / "identity_api.db"
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT metadata_json FROM sessions WHERE session_id = ?",
            ("meta-session",),
        ).fetchone()
        assert row is not None
        payload = json.loads(row[0] or "{}")
        assert "ip_hash" in payload
        assert payload["ip_hash"].startswith("ip_sha:")
        assert "ip" not in payload
    finally:
        conn.close()


def test_adaptive_uses_request_session_id_as_runtime_scope(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def _capture_stub(*_args: Any, **kwargs: Any) -> dict[str, Any]:
        captured["user_id"] = kwargs.get("user_id")
        return _stub_adaptive_result()

    monkeypatch.setattr(routes, "run_multiagent_adaptive_sync", _capture_stub, raising=True)
    headers = {
        "X-API-Key": "test-key-001",
        "X-Session-Id": "identity-session-1",
        "X-Device-Fingerprint": "sha256:runtime-scope-fp",
    }
    response = client.post(
        "/api/v1/questions/adaptive",
        headers=headers,
        json={"query": "test", "session_id": "chat-session-xyz"},
    )
    assert response.status_code == 200
    assert captured.get("user_id") == "chat-session-xyz"
