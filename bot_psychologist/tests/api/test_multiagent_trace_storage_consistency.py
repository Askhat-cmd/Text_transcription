from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from api import dependencies as deps
from api.main import app
import api.routes as routes
from api.session_store import get_session_store
from bot_agent.config import config


DEV_HEADERS = {"X-API-Key": "dev-key-001"}


def _stub_multiagent_runtime(*, query: str, user_id: str, **_kwargs: Any) -> dict[str, Any]:
    debug_payload = {
        "multiagent_enabled": True,
        "pipeline_version": "multiagent_v1",
        "total_latency_ms": 45,
        "timings": {
            "state_analyzer_ms": 5,
            "thread_manager_ms": 4,
            "memory_retrieval_ms": 6,
            "writer_ms": 25,
            "validator_ms": 5,
        },
        "nervous_state": "calm",
        "intent": "support",
        "safety_flag": False,
        "confidence": 0.93,
        "thread_id": "thread-1",
        "phase": "exploring",
        "relation_to_thread": "continue",
        "continuity_score": 0.8,
        "context_turns": 2,
        "semantic_hits_count": 1,
        "has_relevant_knowledge": True,
        "response_mode": "presence",
        "tokens_used": 120,
        "tokens_prompt": 90,
        "tokens_completion": 30,
        "tokens_total": 120,
        "estimated_cost_usd": 0.0009,
        "writer_system_prompt": "system",
        "writer_user_prompt": "user",
        "writer_llm_response_raw": "ok",
        "model_used": "gpt-5-mini",
        "writer_api_mode": "responses",
        "writer_fallback_used": False,
        "state_analyzer_api_mode": "responses",
        "validator_blocked": False,
        "validator_quality_flags": [],
    }
    return {
        "status": "ok",
        "answer": f"multiagent:{query}",
        "state_analysis": {
            "primary_state": "calm",
            "confidence": 0.93,
            "emotional_tone": "",
            "recommendations": [],
        },
        "path_recommendation": None,
        "feedback_prompt": "",
        "concepts": [],
        "sources": [],
        "conversation_context": "ctx",
        "metadata": {
            "runtime": "multiagent",
            "runtime_entrypoint": "multiagent_adapter",
            "legacy_fallback_used": False,
            "pipeline_version": "multiagent_v1",
            "runtime_user_scope": user_id,
            "writer_model": "gpt-5-mini",
            "writer_api_mode": "responses",
        },
        "debug": debug_payload,
        "debug_trace": {
            "session_id": user_id,
            "pipeline_version": "multiagent_v1",
            "multiagent_enabled": True,
            "tokens_total": 120,
            "writer_api_mode": "responses",
            "primary_model": "gpt-5-mini",
        },
        "processing_time_seconds": 0.05,
    }


def _reset_store() -> None:
    store = get_session_store()
    with store._lock:  # type: ignore[attr-defined]
        store._sessions.clear()  # type: ignore[attr-defined]
        store._blobs.clear()  # type: ignore[attr-defined]
        store._multiagent_debug.clear()  # type: ignore[attr-defined]
        store._multiagent_updated.clear()  # type: ignore[attr-defined]
        store._session_stats.clear()  # type: ignore[attr-defined]
        store._session_stats_updated.clear()  # type: ignore[attr-defined]


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _reset_store()
    monkeypatch.setattr(config, "WARMUP_ON_START", False, raising=False)
    monkeypatch.setattr(config, "BOT_DB_PATH", tmp_path / "trace_consistency.db", raising=False)
    monkeypatch.setattr(deps, "_identity_repository", None, raising=False)
    monkeypatch.setattr(deps, "_identity_service", None, raising=False)
    monkeypatch.setattr(deps, "_conversation_repository", None, raising=False)
    monkeypatch.setattr(deps, "_conversation_service", None, raising=False)
    monkeypatch.setattr(routes, "run_multiagent_adaptive_sync", _stub_multiagent_runtime, raising=True)
    with TestClient(app, base_url="http://localhost") as test_client:
        yield test_client


def test_multiagent_trace_endpoint_consistent_with_adaptive_response(client: TestClient) -> None:
    session_id = "trace-session-001"
    response = client.post(
        "/api/v1/questions/adaptive",
        headers=DEV_HEADERS,
        json={"query": "hello", "session_id": session_id, "debug": True},
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["trace"] is not None
    assert payload["metadata"]["runtime"] == "multiagent"

    trace_response = client.get(
        f"/api/debug/session/{session_id}/multiagent-trace",
        headers=DEV_HEADERS,
    )
    assert trace_response.status_code == 200
    trace_payload = trace_response.json()
    assert trace_payload["pipeline_version"] == "multiagent_v1"
    assert trace_payload["writer_llm"]["model"] == "gpt-5-mini"
    assert trace_payload["writer_llm"]["api_mode"] == "responses"


def test_multiagent_trace_endpoint_falls_back_to_latest_when_turn_missing(client: TestClient) -> None:
    session_id = "trace-session-002"
    response = client.post(
        "/api/v1/questions/adaptive",
        headers=DEV_HEADERS,
        json={"query": "turn", "session_id": session_id, "debug": True},
    )
    assert response.status_code == 200

    trace_response = client.get(
        f"/api/debug/session/{session_id}/multiagent-trace?turn_index=999",
        headers=DEV_HEADERS,
    )
    assert trace_response.status_code == 200
    trace_payload = trace_response.json()
    assert trace_payload["pipeline_version"] == "multiagent_v1"
    assert trace_payload["turn_index"] == 1


def test_multiagent_trace_endpoint_returns_diagnostic_payload_when_missing(client: TestClient) -> None:
    response = client.get(
        "/api/debug/session/unknown-session/multiagent-trace",
        headers=DEV_HEADERS,
    )
    assert response.status_code == 404
    payload = response.json()
    assert payload["detail"] == "No multiagent trace found for session"
    assert payload["session_id"] == "unknown-session"
    assert isinstance(payload.get("available_trace_keys"), list)
    assert isinstance(payload.get("searched_trace_keys"), list)
