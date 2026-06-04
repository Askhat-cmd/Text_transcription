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
    monkeypatch.setattr(config, "BOT_DB_PATH", tmp_path / "reset_session.db", raising=False)
    monkeypatch.setattr(deps, "_identity_repository", None, raising=False)
    monkeypatch.setattr(deps, "_identity_service", None, raising=False)
    monkeypatch.setattr(deps, "_conversation_repository", None, raising=False)
    monkeypatch.setattr(deps, "_conversation_service", None, raising=False)
    with TestClient(app, base_url="http://localhost") as test_client:
        yield test_client


def test_reset_context_preserves_session_id_and_clears_turns(client: TestClient, tmp_path: Path) -> None:
    headers = _headers("reset-web-session", "sha256:reset-fp")
    me = client.get("/api/v1/identity/me", headers=headers)
    assert me.status_code == 200
    user_id = me.json()["user_id"]

    manager = SessionManager(str(tmp_path / "reset_session.db"))
    manager.create_session("chat-reset-a", user_id=user_id, metadata={"source": "web_ui", "title": "Chat A"})
    manager.save_turn(
        session_id="chat-reset-a",
        turn_number=1,
        user_input="before",
        bot_response="before answer",
        mode="presence",
    )

    response = client.post(
        "/api/v1/users/user-placeholder/sessions/chat-reset-a/reset-context",
        headers=headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["session_id"] == "chat-reset-a"
    assert payload["recreated"] is True
    assert payload["memory_control_event"] == {
        "event": "current_chat_context_reset",
        "scope": "session_only",
        "user_profile_deleted": False,
    }

    refreshed = manager.load_session("chat-reset-a")
    assert refreshed is not None
    assert refreshed["session_info"]["user_id"] == user_id
    assert refreshed["conversation_turns"] == []


def test_clear_user_memory_profile_returns_explicit_memory_control_event(client: TestClient) -> None:
    headers = _headers("reset-web-session-2", "sha256:reset-fp-2")
    me = client.get("/api/v1/identity/me", headers=headers)
    assert me.status_code == 200
    user_id = me.json()["user_id"]

    response = client.delete(
        f"/api/v1/users/{user_id}/history",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["memory_control_event"] == {
        "event": "user_memory_profile_cleared",
        "scope": "user_profile",
        "user_profile_deleted": True,
    }
