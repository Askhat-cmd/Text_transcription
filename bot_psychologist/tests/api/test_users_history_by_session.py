from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api import dependencies as deps
from api.main import app
from bot_agent.config import config
from bot_agent.storage import SessionManager


def _headers(session_id: str, fingerprint: str) -> dict[str, str]:
    return {
        "X-API-Key": "test-key-001",
        "X-Session-Id": session_id,
        "X-Device-Fingerprint": fingerprint,
    }


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "WARMUP_ON_START", False, raising=False)
    monkeypatch.setattr(config, "BOT_DB_PATH", tmp_path / "history_by_session.db", raising=False)
    monkeypatch.setattr(deps, "_identity_repository", None, raising=False)
    monkeypatch.setattr(deps, "_identity_service", None, raising=False)
    monkeypatch.setattr(deps, "_conversation_repository", None, raising=False)
    monkeypatch.setattr(deps, "_conversation_service", None, raising=False)
    monkeypatch.setattr(deps, "_registration_repository", None, raising=False)
    monkeypatch.setattr(deps, "_registration_service", None, raising=False)
    monkeypatch.setattr(deps, "_database_bootstrap", None, raising=False)
    with TestClient(app, base_url="http://localhost") as test_client:
        yield test_client


def test_history_returns_requested_session_turns(client: TestClient, tmp_path: Path) -> None:
    headers = _headers("web-session-1", "sha256:history-fp-1")
    me = client.get("/api/v1/identity/me", headers=headers)
    assert me.status_code == 200
    user_id = me.json()["user_id"]

    manager = SessionManager(str(tmp_path / "history_by_session.db"))
    manager.create_session("chat-session-a", user_id=user_id)
    manager.create_session("chat-session-b", user_id=user_id)
    manager.save_turn(
        session_id="chat-session-a",
        turn_number=1,
        user_input="A: first",
        bot_response="A: answer",
        mode="presence",
    )
    manager.save_turn(
        session_id="chat-session-b",
        turn_number=1,
        user_input="B: first",
        bot_response="B: answer",
        mode="presence",
    )

    response = client.post(
        "/api/v1/users/chat-session-a/history",
        headers=headers,
        params={"last_n_turns": 10},
    )
    assert response.status_code == 200
    payload = response.json()
    turns = payload["turns"]
    assert payload["total_turns"] == 1
    assert len(turns) == 1
    assert turns[0]["user_input"] == "A: first"
    assert turns[0]["bot_response"] == "A: answer"


def test_history_for_foreign_session_is_forbidden(client: TestClient, tmp_path: Path) -> None:
    headers_user_1 = _headers("web-session-u1", "sha256:history-fp-u1")
    headers_user_2 = _headers("web-session-u2", "sha256:history-fp-u2")

    me_1 = client.get("/api/v1/identity/me", headers=headers_user_1)
    me_2 = client.get("/api/v1/identity/me", headers=headers_user_2)
    assert me_1.status_code == 200
    assert me_2.status_code == 200
    user_2_id = me_2.json()["user_id"]

    manager = SessionManager(str(tmp_path / "history_by_session.db"))
    manager.create_session("foreign-chat-session", user_id=user_2_id)
    manager.save_turn(
        session_id="foreign-chat-session",
        turn_number=1,
        user_input="foreign",
        bot_response="foreign answer",
        mode="presence",
    )

    response = client.post(
        "/api/v1/users/foreign-chat-session/history",
        headers=headers_user_1,
        params={"last_n_turns": 10},
    )
    assert response.status_code == 403
    assert "does not belong" in response.json().get("detail", "")


def test_history_for_unknown_session_returns_empty(client: TestClient) -> None:
    headers = _headers("web-session-empty", "sha256:history-fp-empty")
    me = client.get("/api/v1/identity/me", headers=headers)
    assert me.status_code == 200

    response = client.get(
        "/api/v1/users/non-existing-session-id/history",
        headers=headers,
        params={"last_n_turns": 10},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total_turns"] == 0
    assert payload["turns"] == []
