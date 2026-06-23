from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.main import app
from api.session_store import get_session_store


DEV_HEADERS = {"X-API-Key": "dev-key-001"}


def _reset_store() -> None:
    store = get_session_store()
    with store._lock:  # type: ignore[attr-defined]
        store._sessions.clear()  # type: ignore[attr-defined]
        store._blobs.clear()  # type: ignore[attr-defined]
        store._multiagent_debug.clear()  # type: ignore[attr-defined]
        store._multiagent_updated.clear()  # type: ignore[attr-defined]


def test_multiagent_trace_endpoint_includes_runtime_trace_summary_v1() -> None:
    _reset_store()
    store = get_session_store()
    store.save_multiagent_debug(
        session_id="runtime-summary-session",
        turn_index=1,
        debug={
            "multiagent_enabled": True,
            "pipeline_version": "multiagent_v1",
            "total_latency_ms": 111,
            "turn_index": 1,
            "nervous_state": "calm",
            "intent": "support",
            "safety_flag": False,
            "confidence": 0.9,
            "thread_id": "th-1",
            "phase": "clarify",
            "relation_to_thread": "continue",
            "continuity_score": 0.7,
            "context_turns": 1,
            "semantic_hits_count": 0,
            "semantic_hits_detail": [],
            "conversation_context": "",
            "rag_query": "",
            "response_mode": "reflect",
            "timings": {
                "state_analyzer_ms": 10,
                "thread_manager_ms": 10,
                "memory_retrieval_ms": 10,
                "writer_ms": 70,
                "validator_ms": 11,
            },
            "runtime_trace_summary_v1": {
                "version": "runtime_trace_summary_v1",
                "entrypoint": "multiagent_adapter",
                "latest_turn_constraints": ["no_practice", "simplify"],
                "kb_visible_to_writer": False,
                "semantic_cards_visible_to_writer": False,
                "overlay_apply_detected": False,
                "final_directive_mode": "answer_directly_without_practice",
                "practice_blocked_by_user_request": True,
                "warnings": [],
                "full_trace_available": True,
            },
        },
    )

    with TestClient(app, base_url="http://localhost") as client:
        response = client.get(
            "/api/debug/session/runtime-summary-session/multiagent-trace",
            headers=DEV_HEADERS,
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["runtime_trace_summary_v1"]["entrypoint"] == "multiagent_adapter"
    assert payload["runtime_trace_summary_v1"]["latest_turn_constraints"] == [
        "no_practice",
        "simplify",
    ]
