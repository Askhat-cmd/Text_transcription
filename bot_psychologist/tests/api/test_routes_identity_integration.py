from __future__ import annotations

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
    monkeypatch.setattr(routes, "answer_question_adaptive", _stub_adaptive_result, raising=True)
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
