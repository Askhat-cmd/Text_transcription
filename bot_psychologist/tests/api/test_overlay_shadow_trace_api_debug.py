from __future__ import annotations

import sys
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api import dependencies as deps
from api.main import app
from api.session_store import get_session_store
from bot_agent.config import config


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


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch):
    temp_dir = PROJECT_ROOT / ".tmp_test_artifacts" / f"overlay_shadow_trace_{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(config, "WARMUP_ON_START", False, raising=False)
    monkeypatch.setattr(
        config,
        "BOT_DB_PATH",
        temp_dir / "overlay_shadow_trace.db",
        raising=False,
    )
    monkeypatch.setattr(deps, "_identity_repository", None, raising=False)
    monkeypatch.setattr(deps, "_identity_service", None, raising=False)
    monkeypatch.setattr(deps, "_conversation_repository", None, raising=False)
    monkeypatch.setattr(deps, "_conversation_service", None, raising=False)
    monkeypatch.setattr(deps, "_registration_repository", None, raising=False)
    monkeypatch.setattr(deps, "_registration_service", None, raising=False)
    monkeypatch.setattr(deps, "_database_bootstrap", None, raising=False)
    with TestClient(app, base_url="http://localhost") as test_client:
        yield test_client


def test_multiagent_trace_endpoint_includes_overlay_shadow_when_present(
    client: TestClient,
) -> None:
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
                        "matched_terms": ["РєРѕРЅС‚СЂРѕР»СЊ"],
                        "safe_user_translation_preview": "РџРѕС…РѕР¶Рµ, РєРѕРЅС‚СЂРѕР»СЊ Р·РґРµСЃСЊ СЂР°Р±РѕС‚Р°РµС‚ РєР°Рє Р·Р°С‰РёС‚Р°.",
                        "allowed_writer_use_preview": "РўРѕР»СЊРєРѕ РєР°Рє РјСЏРіРєР°СЏ РіРёРїРѕС‚РµР·Р°.",
                        "trace_only": True,
                    }
                ],
                "warnings": ["evaluation_only_overlay"],
                "safety_flags": ["trace_only"],
                "blockers": [],
            },
            "semantic_cards_pilot": {
                "schema_version": "semantic_cards_pilot_trace_v1",
                "enabled": True,
                "selected_card_count": 1,
                "selected_card_ids": ["program_imperfect_self_v1"],
                "selection_reason": "title/core_thesis/current_turn_overlap",
                "writer_can_ignore": True,
                "applied_as_authority": False,
                "suppressed_reason": "",
                "candidate_scores": [
                    {
                        "card_id": "program_imperfect_self_v1",
                        "score": 5,
                        "reasons": ["current_turn_overlap", "topic_alias"],
                    }
                ],
            },
        },
    )

    response = client.get("/api/debug/session/overlay-session/multiagent-trace", headers=DEV_HEADERS)

    assert response.status_code == 200
    payload = response.json()
    assert payload["overlay_shadow"]["schema_version"] == "overlay_shadow_trace_v1"
    assert payload["overlay_shadow"]["used_for_writer"] is False
    assert payload["overlay_shadow"]["used_for_retrieval_execution"] is False
    assert payload["overlay_shadow"]["matched_candidates"][0]["candidate_id"] == "cand-1"
    assert payload["semantic_cards_pilot"]["schema_version"] == "semantic_cards_pilot_trace_v1"
    assert payload["semantic_cards_pilot"]["selected_card_ids"] == ["program_imperfect_self_v1"]
    assert payload["semantic_cards_pilot"]["writer_can_ignore"] is True
