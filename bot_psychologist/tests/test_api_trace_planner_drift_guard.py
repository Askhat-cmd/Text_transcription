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


def _stub_runtime(*, query: str, user_id: str, **_kwargs: Any) -> dict[str, Any]:
    planner = {
        "version": "response_planner_v1",
        "enabled": True,
        "next_move": "deepen_mechanism",
        "answer_shape": "mechanism_explanation",
        "practice_policy": "forbidden",
        "question_policy": "none",
        "revoicing_policy": "suppressed",
    }
    drift = {
        "version": "planner_drift_guard_v1",
        "enabled": True,
        "status": "ok",
        "severity": "none",
        "flags": [],
    }
    summary = {
        "version": "planner_drift_guard_v1",
        "window_size": 100,
        "total": 1,
        "ok_count": 1,
        "warning_count": 0,
        "critical_count": 0,
        "violation_rate": 0.0,
        "critical_rate": 0.0,
        "by_flag": {},
        "last_status": "ok",
        "last_flags": [],
        "threshold_status": "ok",
    }
    return {
        "status": "ok",
        "answer": f"ok:{query}",
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
        "conversation_context": "ctx",
        "metadata": {"runtime": "multiagent", "runtime_entrypoint": "multiagent_adapter"},
        "debug": {
            "multiagent_enabled": True,
            "pipeline_version": "multiagent_v1",
            "response_planner_version": "response_planner_v1",
            "response_planner": planner,
            "response_planner_error": None,
            "planner_drift_guard_version": "planner_drift_guard_v1",
            "planner_drift_guard": drift,
            "planner_drift_guard_error": None,
            "planner_drift_summary": summary,
            "timings": {
                "state_analyzer_ms": 1,
                "thread_manager_ms": 1,
                "memory_retrieval_ms": 1,
                "writer_ms": 1,
                "validator_ms": 1,
            },
        },
        "debug_trace": {
            "session_id": user_id,
            "response_planner_version": "response_planner_v1",
            "response_planner": planner,
            "response_planner_error": None,
            "planner_drift_guard_version": "planner_drift_guard_v1",
            "planner_drift_guard": drift,
            "planner_drift_guard_error": None,
            "planner_drift_summary": summary,
        },
        "processing_time_seconds": 0.01,
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
    monkeypatch.setattr(config, "BOT_DB_PATH", tmp_path / "trace_planner_drift.db", raising=False)
    monkeypatch.setattr(deps, "_identity_repository", None, raising=False)
    monkeypatch.setattr(deps, "_identity_service", None, raising=False)
    monkeypatch.setattr(deps, "_conversation_repository", None, raising=False)
    monkeypatch.setattr(deps, "_conversation_service", None, raising=False)
    monkeypatch.setattr(routes, "run_multiagent_adaptive_sync", _stub_runtime, raising=True)
    with TestClient(app, base_url="http://localhost") as test_client:
        yield test_client


def test_api_trace_keeps_planner_drift_payload(client: TestClient) -> None:
    session_id = "pdg-trace-001"
    response = client.post(
        "/api/v1/questions/adaptive",
        headers=DEV_HEADERS,
        json={"query": "hello", "session_id": session_id, "debug": True},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["trace"]["planner_drift_guard_version"] == "planner_drift_guard_v1"
    assert payload["trace"]["planner_drift_guard"]["status"] == "ok"
    assert payload["trace"].get("planner_drift_guard_error") is None

    traces_response = client.get(f"/api/debug/session/{session_id}/traces", headers=DEV_HEADERS)
    assert traces_response.status_code == 200
    traces_payload = traces_response.json()
    last_trace = traces_payload["traces"][-1]
    assert last_trace["planner_drift_guard_version"] == "planner_drift_guard_v1"
    assert last_trace["planner_drift_guard"]["status"] == "ok"
