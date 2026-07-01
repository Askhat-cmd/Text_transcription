from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api import dependencies as deps
from api.main import app
import api.routes as routes
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


def _build_runtime_stub() -> Any:
    turns_by_session: dict[str, int] = {}

    def _stub_runtime(*, query: str, user_id: str, **_kwargs: Any) -> dict[str, Any]:
        turn_number = turns_by_session.get(user_id, 0) + 1
        turns_by_session[user_id] = turn_number
        answer = f"stub answer {turn_number}: {query}"

        return {
            "status": "ok",
            "answer": answer,
            "state_analysis": {
                "primary_state": "calm",
                "confidence": 0.91,
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
                "recommended_mode": "PRESENCE",
            },
            "debug": {
                "multiagent_enabled": True,
                "pipeline_version": "multiagent_v1",
                "total_latency_ms": 12,
                "timings": {
                    "state_analyzer_ms": 2,
                    "thread_manager_ms": 2,
                    "memory_retrieval_ms": 2,
                    "writer_ms": 4,
                    "validator_ms": 2,
                },
                "nervous_state": "calm",
                "intent": "support",
                "safety_flag": False,
                "confidence": 0.91,
                "thread_id": "thread-1",
                "phase": "exploring",
                "relation_to_thread": "continue",
                "continuity_score": 0.8,
                "context_turns": turn_number,
                "semantic_hits_count": 0,
                "has_relevant_knowledge": False,
                "response_mode": "presence",
                "tokens_total": 40,
                "model_used": "gpt-5-mini",
                "writer_api_mode": "responses",
            },
            "debug_trace": {
                "session_id": user_id,
                "pipeline_version": "multiagent_v1",
                "multiagent_enabled": True,
                "recommended_mode": "PRESENCE",
                "writer_api_mode": "responses",
                "primary_model": "gpt-5-mini",
            },
            "processing_time_seconds": 0.01,
        }

    return _stub_runtime


def _collect_sse_events(response_text: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for block in [chunk for chunk in response_text.split("\n\n") if chunk.strip()]:
        event_type = "message"
        payload: dict[str, Any] | None = None
        for line in block.splitlines():
            stripped = line.strip()
            if stripped.startswith("event:"):
                event_type = stripped.replace("event:", "", 1).strip() or "message"
            elif stripped.startswith("data:"):
                raw = stripped.replace("data:", "", 1).strip()
                if not raw:
                    continue
                payload = json.loads(raw)
        if payload is not None:
            events.append({"type": event_type, "data": payload})
    return events


def _extract_event_payload(events: list[dict[str, Any]], event_type: str) -> dict[str, Any]:
    for event in events:
        if event["type"] == event_type:
            return dict(event["data"])
    raise AssertionError(f"Missing SSE event: {event_type}")


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    _reset_store()
    monkeypatch.setattr(config, "WARMUP_ON_START", False, raising=False)
    monkeypatch.setattr(config, "ENABLE_STREAMING", True, raising=False)
    monkeypatch.setattr(config, "BOT_DB_PATH", tmp_path / "prd_047_36_hf4_every_turn.db", raising=False)
    monkeypatch.setattr(deps, "_identity_repository", None, raising=False)
    monkeypatch.setattr(deps, "_identity_service", None, raising=False)
    monkeypatch.setattr(deps, "_conversation_repository", None, raising=False)
    monkeypatch.setattr(deps, "_conversation_service", None, raising=False)
    monkeypatch.setattr(routes, "run_multiagent_adaptive_sync", _build_runtime_stub(), raising=True)
    with TestClient(app, base_url="http://localhost") as test_client:
        yield test_client


def test_stream_trace_persists_for_every_fresh_assistant_turn(client: TestClient) -> None:
    session_id = "hf4-fresh-chat"
    prompts = [
        "Что такое душа?",
        "А чем душа отличается от сознания?",
        "В чем смысл жизни?",
        "Например моя семья помогает мне преодолевать трудности",
        "А что об этом говорится в Нейросталкинге?",
    ]

    delivered_turns: list[int] = []
    for expected_turn, prompt in enumerate(prompts, start=1):
        response = client.post(
            "/api/v1/questions/adaptive-stream",
            headers={**DEV_HEADERS, "X-Session-Id": session_id},
            json={"query": prompt, "session_id": session_id, "debug": True},
        )
        assert response.status_code == 200
        events = _collect_sse_events(response.text)
        done_payload = next(event["data"] for event in events if event["data"].get("done") is True)
        trace_payload = _extract_event_payload(events, "trace")

        delivered_turns.append(int(done_payload["turn_number"]))
        assert done_payload["turn_number"] == expected_turn
        assert trace_payload["turn_number"] == expected_turn

        trace_response = client.get(
            f"/api/debug/session/{session_id}/multiagent-trace?turn_index={expected_turn}",
            headers=DEV_HEADERS,
        )
        assert trace_response.status_code == 200
        exact_trace = trace_response.json()
        assert exact_trace["turn_index"] == expected_turn
        assert exact_trace["trace_availability"]["status"] == "available"
        assert exact_trace["trace_availability"]["exact_turn_match"] is True
        assert exact_trace["trace_availability"]["resolved_turn_index"] == expected_turn

    history_response = client.get(
        f"/api/v1/users/{session_id}/history?last_n_turns=10",
        headers={**DEV_HEADERS, "X-Session-Id": session_id},
    )
    assert history_response.status_code == 200
    history_turns = [int(turn["turn_number"]) for turn in history_response.json()["turns"]]

    store = get_session_store()
    stored_debug_turns = store.get_multiagent_debug_turn_indices(session_id)
    available_turn_indices = [
        int(
            client.get(
                f"/api/debug/session/{session_id}/multiagent-trace?turn_index={turn_number}",
                headers=DEV_HEADERS,
            ).json()["trace_availability"]["resolved_turn_index"]
        )
        for turn_number in delivered_turns
    ]

    assert delivered_turns == [1, 2, 3, 4, 5]
    assert history_turns == [1, 2, 3, 4, 5]
    assert stored_debug_turns == [1, 2, 3, 4, 5]
    assert available_turn_indices == [1, 2, 3, 4, 5]
