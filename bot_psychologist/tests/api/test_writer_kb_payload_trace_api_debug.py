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


def test_multiagent_trace_endpoint_includes_writer_kb_payload_trace() -> None:
    _reset_store()
    store = get_session_store()
    store.save_multiagent_debug(
        session_id="writer-kb-session",
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
            "semantic_hits_count": 1,
            "semantic_hits_detail": [],
            "conversation_context": "",
            "rag_query": "что такое нейросталкинг",
            "response_mode": "reflect",
            "timings": {
                "state_analyzer_ms": 10,
                "thread_manager_ms": 10,
                "memory_retrieval_ms": 10,
                "writer_ms": 70,
                "validator_ms": 11,
            },
            "writer_kb_payload_trace": {
                "schema_version": "writer_kb_payload_trace_v1",
                "enabled": True,
                "primary_path": "writer_kb_payload_v1",
                "input_rag_for_writer_count": 1,
                "payload_chunk_count": 1,
                "total_original_char_count": 2480,
                "total_sent_char_count": 1260,
                "payload_sent_to_writer_char_count": 1260,
                "payload_display_preview_char_count": 500,
                "payload_display_is_preview": True,
                "truncated_chunk_count": 1,
                "mid_sentence_cut_count": 0,
                "overlay_metadata_used_count": 0,
                "warnings": [],
                "blockers": [],
            },
            "runtime_config_trace": {
                "schema_version": "runtime_config_trace_v1",
                "app_env": "local",
                "writer_kb_payload_enabled": True,
                "writer_kb_payload_enabled_source": "default_local",
            },
            "future_graduation_notes": {
                "schema_version": "writer_kb_payload_future_graduation_notes_v1",
                "payload_source": "legacy_selected_hit",
            },
        },
    )

    with TestClient(app, base_url="http://localhost") as client:
        response = client.get("/api/debug/session/writer-kb-session/multiagent-trace", headers=DEV_HEADERS)

    assert response.status_code == 200
    payload = response.json()
    assert payload["runtime_config_trace"]["writer_kb_payload_enabled"] is True
    assert payload["writer_kb_payload_trace"]["payload_chunk_count"] == 1
    assert payload["writer_kb_payload_trace"]["primary_path"] == "writer_kb_payload_v1"
    assert payload["future_graduation_notes"]["payload_source"] == "legacy_selected_hit"
