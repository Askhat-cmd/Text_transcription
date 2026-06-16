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
        store._session_stats.clear()  # type: ignore[attr-defined]
        store._session_stats_updated.clear()  # type: ignore[attr-defined]


def test_multiagent_trace_endpoint_includes_overlay_shadow_when_present() -> None:
    _reset_store()
    store = get_session_store()
    store.save_multiagent_debug(
        session_id="overlay-session",
        turn_index=1,
        debug={
            "multiagent_enabled": True,
            "pipeline_version": "multiagent_v1",
            "total_latency_ms": 120,
            "turn_index": 1,
            "nervous_state": "calm",
            "intent": "support",
            "safety_flag": False,
            "confidence": 0.88,
            "thread_id": "th-1",
            "phase": "clarify",
            "relation_to_thread": "continue",
            "continuity_score": 0.7,
            "context_turns": 2,
            "semantic_hits_count": 1,
            "semantic_hits_detail": [
                {
                    "chunk_id": "c1",
                    "source": "doc_1",
                    "score": 0.88,
                    "content_preview": "preview",
                    "content_full": "full",
                }
            ],
            "conversation_context": "User: hi\nAssistant: hello",
            "rag_query": "hi hello",
            "response_mode": "presence",
            "tokens_total": 10,
            "timings": {
                "state_analyzer_ms": 10,
                "thread_manager_ms": 10,
                "memory_retrieval_ms": 20,
                "writer_ms": 60,
                "validator_ms": 20,
            },
            "overlay_shadow": {
                "schema_version": "overlay_shadow_trace_v1",
                "enabled": True,
                "status": "ok",
                "mode": "trace_only",
                "overlay_source_prd": "PRD-047.20",
                "batch_id": "batch_1",
                "overlay_item_count": 12,
                "used_for_writer": False,
                "used_for_retrieval_execution": False,
                "used_for_final_answer": False,
                "would_help": True,
                "match_count": 1,
                "matched_candidates": [
                    {
                        "candidate_id": "cand-1",
                        "chunk_type": "mechanism",
                        "score": 4.2,
                        "matched_terms": ["контроль"],
                        "safe_user_translation_preview": "Похоже, контроль здесь работает как защита.",
                        "allowed_writer_use_preview": "Только как мягкая гипотеза.",
                        "trace_only": True,
                    }
                ],
                "warnings": ["evaluation_only_overlay"],
                "safety_flags": ["trace_only"],
                "blockers": [],
            },
        },
    )

    with TestClient(app, base_url="http://localhost") as client:
        response = client.get("/api/debug/session/overlay-session/multiagent-trace", headers=DEV_HEADERS)

    assert response.status_code == 200
    payload = response.json()
    assert payload["overlay_shadow"]["schema_version"] == "overlay_shadow_trace_v1"
    assert payload["overlay_shadow"]["used_for_writer"] is False
    assert payload["overlay_shadow"]["used_for_retrieval_execution"] is False
    assert payload["overlay_shadow"]["matched_candidates"][0]["candidate_id"] == "cand-1"
