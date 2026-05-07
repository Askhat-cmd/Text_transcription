from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

import api.routes as routes
from api import dependencies as deps
from api.main import app
from api.models import (
    DebugTrace,
    MemoryRetrievalTrace,
    MultiAgentPipelineTrace,
    MultiAgentTraceResponse,
    StateAnalyzerTrace,
    ThreadManagerTrace,
    ValidatorTrace,
    WriterTrace,
)
from api.session_store import get_session_store
from bot_agent.config import config


DEV_HEADERS = {"X-API-Key": "dev-key-001"}


def test_debug_trace_model_keeps_thread_diagnostics_fields() -> None:
    trace = DebugTrace(
        chunks_retrieved=[],
        llm_calls=[],
        context_written_to_memory="ctx",
        total_duration_ms=10,
        thread_diagnostics_version="thread_diagnostics_v1",
        thread_diagnostics={"version": "thread_diagnostics_v1", "summary_flags": ["phase_transition"]},
    )
    payload = trace.model_dump(exclude_none=True)
    assert payload["thread_diagnostics_version"] == "thread_diagnostics_v1"
    assert payload["thread_diagnostics"]["summary_flags"] == ["phase_transition"]


def test_multiagent_trace_response_model_keeps_thread_diagnostics_fields() -> None:
    response = MultiAgentTraceResponse(
        session_id="s1",
        pipeline_version="multiagent_v1",
        total_latency_ms=10,
        agents=MultiAgentPipelineTrace(
            state_analyzer=StateAnalyzerTrace(
                latency_ms=1,
                nervous_state="window",
                intent="explore",
                safety_flag=False,
                confidence=0.9,
            ),
            thread_manager=ThreadManagerTrace(
                latency_ms=1,
                thread_id="t1",
                phase="clarify",
                relation_to_thread="continue",
                continuity_score=0.3,
            ),
            memory_retrieval=MemoryRetrievalTrace(
                latency_ms=1,
                context_turns=1,
                semantic_hits_count=0,
                has_relevant_knowledge=False,
            ),
            writer=WriterTrace(latency_ms=1, response_mode="reflect"),
            validator=ValidatorTrace(latency_ms=1, is_blocked=False),
        ),
        thread_diagnostics_version="thread_diagnostics_v1",
        thread_diagnostics={"version": "thread_diagnostics_v1", "summary_flags": []},
    )
    payload = response.model_dump(exclude_none=True)
    assert payload["thread_diagnostics_version"] == "thread_diagnostics_v1"
    assert isinstance(payload["thread_diagnostics"], dict)


def _stub_multiagent_runtime(*, query: str, user_id: str, **_kwargs: Any) -> dict[str, Any]:
    debug_payload = {
        "multiagent_enabled": True,
        "pipeline_version": "multiagent_v1",
        "total_latency_ms": 40,
        "timings": {
            "state_analyzer_ms": 5,
            "thread_manager_ms": 5,
            "memory_retrieval_ms": 10,
            "writer_ms": 15,
            "validator_ms": 5,
        },
        "nervous_state": "window",
        "intent": "explore",
        "safety_flag": False,
        "confidence": 0.9,
        "thread_id": "t-1",
        "phase": "clarify",
        "relation_to_thread": "continue",
        "continuity_score": 0.5,
        "response_mode": "reflect",
        "context_turns": 1,
        "semantic_hits_count": 0,
        "has_relevant_knowledge": False,
        "validator_blocked": False,
        "validator_quality_flags": [],
        "thread_diagnostics_version": "thread_diagnostics_v1",
        "thread_diagnostics": {
            "version": "thread_diagnostics_v1",
            "relation": {"relation_reason": "continuity_continue"},
            "phase": {"phase_reason": "keep_current_phase"},
            "mode": {"mode_reason": "phase_clarify_reflect"},
            "loops": {},
            "action": {"thread_action": "continue_thread"},
            "summary_flags": [],
        },
    }
    return {
        "status": "ok",
        "answer": f"ok:{query}",
        "state_analysis": {
            "primary_state": "window",
            "confidence": 0.9,
            "emotional_tone": "",
            "recommendations": [],
        },
        "path_recommendation": None,
        "feedback_prompt": "",
        "concepts": [],
        "sources": [],
        "conversation_context": "",
        "metadata": {
            "runtime": "multiagent",
            "runtime_entrypoint": "multiagent_adapter",
            "pipeline_version": "multiagent_v1",
            "runtime_user_scope": user_id,
        },
        "debug": debug_payload,
        "debug_trace": {
            "session_id": user_id,
            "pipeline_version": "multiagent_v1",
            "multiagent_enabled": True,
        },
        "processing_time_seconds": 0.04,
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
    monkeypatch.setattr(config, "BOT_DB_PATH", tmp_path / "thread_diag_contract.db", raising=False)
    monkeypatch.setattr(deps, "_identity_repository", None, raising=False)
    monkeypatch.setattr(deps, "_identity_service", None, raising=False)
    monkeypatch.setattr(deps, "_conversation_repository", None, raising=False)
    monkeypatch.setattr(deps, "_conversation_service", None, raising=False)
    monkeypatch.setattr(routes, "run_multiagent_adaptive_sync", _stub_multiagent_runtime, raising=True)
    with TestClient(app, base_url="http://localhost") as test_client:
        yield test_client


def test_thread_diagnostics_present_in_adaptive_trace_and_debug_endpoint(client: TestClient) -> None:
    session_id = "thread-diag-session-1"
    response = client.post(
        "/api/v1/questions/adaptive",
        headers=DEV_HEADERS,
        json={"query": "hello", "session_id": session_id, "debug": True},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["trace"]["thread_diagnostics_version"] == "thread_diagnostics_v1"
    assert payload["trace"]["thread_diagnostics"]["action"]["thread_action"] == "continue_thread"

    trace_response = client.get(
        f"/api/debug/session/{session_id}/multiagent-trace",
        headers=DEV_HEADERS,
    )
    assert trace_response.status_code == 200
    trace_payload = trace_response.json()
    assert trace_payload["thread_diagnostics_version"] == "thread_diagnostics_v1"
    assert trace_payload["thread_diagnostics"]["mode"]["mode_reason"] == "phase_clarify_reflect"

