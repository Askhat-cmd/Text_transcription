from __future__ import annotations

from pathlib import Path
from typing import Any
import sys
import types

import pytest
from fastapi.testclient import TestClient

try:
    import argon2  # type: ignore  # noqa: F401
except ModuleNotFoundError:
    fake_argon2 = types.ModuleType("argon2")
    fake_exceptions = types.ModuleType("argon2.exceptions")

    class Argon2Error(Exception):
        pass

    class VerifyMismatchError(Argon2Error):
        pass

    class PasswordHasher:
        def hash(self, plain_key: str) -> str:
            return f"fake-argon2::{plain_key}"

        def verify(self, hashed_key: str, plain_key: str) -> bool:
            expected = f"fake-argon2::{plain_key}"
            if hashed_key != expected:
                raise VerifyMismatchError("hash mismatch")
            return True

    fake_argon2.PasswordHasher = PasswordHasher
    fake_exceptions.Argon2Error = Argon2Error
    fake_exceptions.VerifyMismatchError = VerifyMismatchError

    sys.modules["argon2"] = fake_argon2
    sys.modules["argon2.exceptions"] = fake_exceptions

from api import dependencies as deps
from api.main import app
import api.routes as routes
from bot_agent.config import config
from bot_agent.storage import SessionManager


def _headers(session_id: str, fingerprint: str) -> dict[str, str]:
    return {
        "X-API-Key": "test-key-001",
        "X-Session-Id": session_id,
        "X-Device-Fingerprint": fingerprint,
    }


def _stub_multiagent_runtime_factory(db_path: Path):
    manager = SessionManager(str(db_path))

    def _stub(*, query: str, user_id: str, **_kwargs: Any) -> dict[str, Any]:
        session_id = user_id
        payload = manager.load_session(session_id) or {}
        turns = payload.get("conversation_turns", [])
        next_turn = len(turns) + 1
        manager.save_turn(
            session_id=session_id,
            turn_number=next_turn,
            user_input=query,
            bot_response=f"answer:{query}",
            mode="presence",
            user_state="calm",
        )
        return {
            "status": "ok",
            "answer": f"answer:{query}",
            "state_analysis": {
                "primary_state": "calm",
                "confidence": 0.9,
                "emotional_tone": "",
                "recommendations": [],
            },
            "path_recommendation": None,
            "feedback_prompt": "",
            "concepts": [],
            "sources": [],
            "conversation_context": "stub-context",
            "metadata": {
                "runtime_entrypoint": "multiagent_adapter",
                "legacy_fallback_used": False,
                "pipeline_version": "multiagent_v1",
                "recommended_mode": "presence",
            },
            "debug": {
                "multiagent_enabled": True,
                "runtime_entrypoint": "multiagent_adapter",
                "legacy_fallback_used": False,
            },
            "processing_time_seconds": 0.01,
        }

    return _stub


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "chat_session_roundtrip.db"

    monkeypatch.setattr(config, "WARMUP_ON_START", False, raising=False)
    monkeypatch.setattr(config, "BOT_DB_PATH", db_path, raising=False)
    monkeypatch.setattr(deps, "_identity_repository", None, raising=False)
    monkeypatch.setattr(deps, "_identity_service", None, raising=False)
    monkeypatch.setattr(deps, "_conversation_repository", None, raising=False)
    monkeypatch.setattr(deps, "_conversation_service", None, raising=False)
    monkeypatch.setattr(deps, "_registration_repository", None, raising=False)
    monkeypatch.setattr(deps, "_registration_service", None, raising=False)
    monkeypatch.setattr(deps, "_database_bootstrap", None, raising=False)
    monkeypatch.setattr(
        routes,
        "run_multiagent_adaptive_sync",
        _stub_multiagent_runtime_factory(db_path),
        raising=True,
    )

    with TestClient(app, base_url="http://localhost") as test_client:
        yield test_client


def test_created_session_history_roundtrip(client: TestClient) -> None:
    headers = _headers("web-session-roundtrip", "sha256:roundtrip-fp")

    me = client.get("/api/v1/identity/me", headers=headers)
    assert me.status_code == 200
    user_id = me.json()["user_id"]

    create_a = client.post(
        f"/api/v1/users/{user_id}/sessions",
        headers=headers,
        json={},
    )
    assert create_a.status_code == 200
    session_a = create_a.json()["session_id"]

    ask = client.post(
        "/api/v1/questions/adaptive",
        headers=headers,
        json={
            "query": "roundtrip question",
            "user_id": user_id,
            "session_id": session_a,
            "debug": False,
        },
    )
    assert ask.status_code == 200

    history_a_1 = client.get(
        f"/api/v1/users/{session_a}/history",
        headers=headers,
        params={"last_n_turns": 10},
    )
    assert history_a_1.status_code == 200
    payload_a_1 = history_a_1.json()
    assert payload_a_1["total_turns"] >= 1
    assert len(payload_a_1["turns"]) >= 1
    assert payload_a_1["turns"][-1]["turn_number"] == 1

    create_b = client.post(
        f"/api/v1/users/{user_id}/sessions",
        headers=headers,
        json={},
    )
    assert create_b.status_code == 200
    session_b = create_b.json()["session_id"]

    history_b = client.get(
        f"/api/v1/users/{session_b}/history",
        headers=headers,
        params={"last_n_turns": 10},
    )
    assert history_b.status_code == 200
    payload_b = history_b.json()
    assert payload_b["total_turns"] == 0
    assert payload_b["turns"] == []

    history_a_2 = client.get(
        f"/api/v1/users/{session_a}/history",
        headers=headers,
        params={"last_n_turns": 10},
    )
    assert history_a_2.status_code == 200
    payload_a_2 = history_a_2.json()
    assert payload_a_2["total_turns"] >= 1
    assert payload_a_2["turns"][-1]["turn_number"] == 1
    assert payload_a_2["turns"][-1]["user_input"] == "roundtrip question"
