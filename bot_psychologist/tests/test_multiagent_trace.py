from __future__ import annotations

import asyncio
import importlib
from pathlib import Path
import sys
from types import SimpleNamespace

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.main import app
from api.routes.chat import _resolve_multiagent_turn_index
from api.session_store import get_session_store

orchestrator_module = importlib.import_module("bot_agent.multiagent.orchestrator")


DEV_HEADERS = {"X-API-Key": "dev-key-001"}
USER_HEADERS = {"X-API-Key": "user-key-001"}


def _reset_store() -> None:
    store = get_session_store()
    with store._lock:  # type: ignore[attr-defined]
        store._sessions.clear()  # type: ignore[attr-defined]
        store._blobs.clear()  # type: ignore[attr-defined]
        store._multiagent_debug.clear()  # type: ignore[attr-defined]
        store._multiagent_updated.clear()  # type: ignore[attr-defined]


def test_orchestrator_returns_multiagent_timings(monkeypatch) -> None:
    async def fake_analyze(**_kwargs):
        return SimpleNamespace(
            nervous_state="calm",
            intent="support",
            safety_flag=False,
            confidence=0.91,
        )

    async def fake_update_thread(**_kwargs):
        return SimpleNamespace(
            thread_id="thread-test",
            phase="exploring",
            response_mode="presence",
            relation_to_thread="continue",
            continuity_score=0.77,
        )

    async def fake_assemble(**_kwargs):
        return SimpleNamespace(
            has_relevant_knowledge=True,
            context_turns=2,
            semantic_hits=[{"id": "hit-1"}],
        )

    async def fake_write(_contract):
        return "тестовый ответ"

    def fake_validate(_draft, _contract):
        return SimpleNamespace(
            is_blocked=False,
            block_reason=None,
            quality_flags=[],
            safe_replacement=None,
        )

    async def fake_memory_update(**_kwargs):
        return None

    def fake_create_task(coro):
        coro.close()
        return None

    monkeypatch.setattr(orchestrator_module.state_analyzer_agent, "analyze", fake_analyze)
    monkeypatch.setattr(orchestrator_module.thread_manager_agent, "update", fake_update_thread)
    monkeypatch.setattr(orchestrator_module.memory_retrieval_agent, "assemble", fake_assemble)
    monkeypatch.setattr(orchestrator_module.writer_agent, "write", fake_write)
    monkeypatch.setattr(orchestrator_module.validator_agent, "validate", fake_validate)
    monkeypatch.setattr(orchestrator_module.memory_retrieval_agent, "update", fake_memory_update)
    monkeypatch.setattr(orchestrator_module.asyncio, "create_task", fake_create_task)
    monkeypatch.setattr(orchestrator_module.thread_storage, "load_active", lambda _user_id: None)
    monkeypatch.setattr(orchestrator_module.thread_storage, "load_archived", lambda _user_id: [])
    monkeypatch.setattr(orchestrator_module.thread_storage, "archive_thread", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(orchestrator_module.thread_storage, "save_active", lambda *_args, **_kwargs: None)

    result = asyncio.run(orchestrator_module.orchestrator.run(query="привет", user_id="u-test"))
    debug = result["debug"]
    timings = debug.get("timings", {})

    assert debug["pipeline_version"] == "multiagent_v1"
    assert isinstance(debug.get("total_latency_ms"), int)
    assert isinstance(timings.get("state_analyzer_ms"), int)
    assert isinstance(timings.get("thread_manager_ms"), int)
    assert isinstance(timings.get("memory_retrieval_ms"), int)
    assert isinstance(timings.get("writer_ms"), int)
    assert isinstance(timings.get("validator_ms"), int)


def test_session_store_multiagent_debug_roundtrip() -> None:
    _reset_store()
    store = get_session_store()
    store.save_multiagent_debug(
        session_id="ma-session",
        turn_index=3,
        debug={"multiagent_enabled": True, "pipeline_version": "multiagent_v1"},
    )

    by_turn = store.get_multiagent_debug("ma-session", 3)
    latest = store.get_latest_multiagent_debug("ma-session")

    assert by_turn is not None
    assert by_turn["turn_index"] == 3
    assert latest is not None
    assert latest["pipeline_version"] == "multiagent_v1"


def test_multiagent_trace_endpoint_returns_200() -> None:
    _reset_store()
    store = get_session_store()
    store.save_multiagent_debug(
        session_id="ma-session",
        turn_index=1,
        debug={
            "multiagent_enabled": True,
            "pipeline_version": "multiagent_v1",
            "total_latency_ms": 1200,
            "turn_index": 1,
            "nervous_state": "calm",
            "intent": "support",
            "safety_flag": False,
            "confidence": 0.88,
            "thread_id": "th-1",
            "phase": "exploring",
            "relation_to_thread": "continue",
            "continuity_score": 0.7,
            "context_turns": 2,
            "semantic_hits_count": 1,
            "has_relevant_knowledge": True,
            "response_mode": "presence",
            "tokens_used": 321,
            "model_used": "gpt-5-mini",
            "validator_blocked": False,
            "validator_block_reason": None,
            "validator_quality_flags": [],
            "timings": {
                "state_analyzer_ms": 100,
                "thread_manager_ms": 50,
                "memory_retrieval_ms": 200,
                "writer_ms": 800,
                "validator_ms": 50,
            },
        },
    )

    with TestClient(app, base_url="http://localhost") as client:
        response = client.get("/api/debug/session/ma-session/multiagent-trace", headers=DEV_HEADERS)

    assert response.status_code == 200
    payload = response.json()
    assert payload["pipeline_version"] == "multiagent_v1"
    assert payload["agents"]["state_analyzer"]["nervous_state"] == "calm"
    assert payload["agents"]["writer"]["tokens_used"] == 321


def test_multiagent_trace_endpoint_requires_dev_key() -> None:
    _reset_store()
    store = get_session_store()
    store.save_multiagent_debug(
        session_id="ma-session",
        turn_index=1,
        debug={"multiagent_enabled": True, "pipeline_version": "multiagent_v1"},
    )

    with TestClient(app, base_url="http://localhost") as client:
        response = client.get("/api/debug/session/ma-session/multiagent-trace", headers=USER_HEADERS)

    assert response.status_code == 403


def test_multiagent_trace_endpoint_returns_409_for_legacy_session() -> None:
    _reset_store()
    store = get_session_store()
    store.save_multiagent_debug(
        session_id="legacy-session",
        turn_index=2,
        debug={"multiagent_enabled": False},
    )

    with TestClient(app, base_url="http://localhost") as client:
        response = client.get("/api/debug/session/legacy-session/multiagent-trace", headers=DEV_HEADERS)

    assert response.status_code == 409


def test_resolve_multiagent_turn_index_uses_next_turn_when_debug_trace_missing() -> None:
    _reset_store()
    store = get_session_store()
    store.append_trace("s-turn", {"turn_number": 1})
    store.append_trace("s-turn", {"turn_number": 2})

    resolved = _resolve_multiagent_turn_index(
        result={"debug": {"multiagent_enabled": True}},
        store=store,
        session_id="s-turn",
    )

    assert resolved == 3


def test_resolve_multiagent_turn_index_ignores_stale_debug_turn_number() -> None:
    _reset_store()
    store = get_session_store()
    store.append_trace("s-stale", {"turn_number": 1})
    store.append_trace("s-stale", {"turn_number": 2})

    resolved = _resolve_multiagent_turn_index(
        result={"debug_trace": {"turn_number": 1}},
        store=store,
        session_id="s-stale",
    )

    assert resolved == 3
