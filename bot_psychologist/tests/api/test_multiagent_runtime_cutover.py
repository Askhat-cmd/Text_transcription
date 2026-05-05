from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from api import dependencies as deps
from api.main import app
from api.routes import common as common_routes
import api.routes as routes
import bot_agent.answer_adaptive as legacy_adaptive
from bot_agent.config import config


def _stub_multiagent_runtime(*, query: str, user_id: str, **_kwargs: Any) -> dict[str, Any]:
    return {
        "status": "ok",
        "answer": f"multiagent:{query}",
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
        "conversation_context": "stub-context",
        "metadata": {
            "runtime": "multiagent",
            "runtime_entrypoint": "multiagent_adapter",
            "legacy_fallback_used": False,
            "pipeline_version": "multiagent_v1",
            "recommended_mode": "reflect",
            "runtime_user_scope": user_id,
        },
        "debug": {
            "multiagent_enabled": True,
            "pipeline_version": "multiagent_v1",
            "runtime_entrypoint": "multiagent_adapter",
            "legacy_fallback_used": False,
            "direct_multiagent_cutover": True,
            "state_analyzer_fallback_used": False,
            "nervous_state": "calm",
            "confidence": 0.91,
            "conversation_context": "stub-context",
        },
        "processing_time_seconds": 0.01,
    }


def _collect_sse_events(response_text: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    blocks = [chunk for chunk in response_text.split("\n\n") if chunk.strip()]
    for block in blocks:
        event_type = "message"
        payload: dict[str, Any] | None = None
        for line in block.splitlines():
            line = line.strip()
            if line.startswith("event:"):
                event_type = line.replace("event:", "", 1).strip() or "message"
            elif line.startswith("data:"):
                raw = line.replace("data:", "", 1).strip()
                if not raw:
                    continue
                try:
                    payload = json.loads(raw)
                except json.JSONDecodeError:
                    payload = None
        if payload is not None:
            events.append({"type": event_type, "data": payload})
    return events


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "WARMUP_ON_START", False, raising=False)
    monkeypatch.setattr(config, "BOT_DB_PATH", tmp_path / "runtime_cutover_identity.db", raising=False)
    monkeypatch.setattr(deps, "_identity_repository", None, raising=False)
    monkeypatch.setattr(deps, "_identity_service", None, raising=False)
    monkeypatch.setattr(deps, "_conversation_repository", None, raising=False)
    monkeypatch.setattr(deps, "_conversation_service", None, raising=False)
    monkeypatch.setattr(routes, "run_multiagent_adaptive_sync", _stub_multiagent_runtime, raising=True)
    monkeypatch.setattr(routes, "answer_question_adaptive", _stub_multiagent_runtime, raising=True)
    monkeypatch.setattr(common_routes, "run_multiagent_adaptive_sync", _stub_multiagent_runtime, raising=True)
    with TestClient(app, base_url="http://localhost") as test_client:
        yield test_client


def test_adaptive_endpoint_does_not_call_legacy_answer_adaptive(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _boom(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("legacy answer_adaptive must not be called")

    monkeypatch.setattr(legacy_adaptive, "answer_question_adaptive", _boom, raising=True)

    response = client.post(
        "/api/v1/questions/adaptive",
        headers={"X-API-Key": "test-key-001"},
        json={"query": "test query", "debug": True},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"].startswith("multiagent:")
    assert payload["metadata"]["runtime"] == "multiagent"
    assert payload["metadata"]["runtime_entrypoint"] == "multiagent_adapter"
    assert payload["metadata"]["legacy_fallback_used"] is False
    assert payload["trace"]["direct_multiagent_cutover"] is True
    assert payload["trace"]["legacy_fallback_used"] is False
    assert payload["trace"]["state_analyzer_fallback_used"] is False


@pytest.mark.parametrize(
    "endpoint",
    [
        "/api/v1/questions/basic",
        "/api/v1/questions/basic-with-semantic",
        "/api/v1/questions/graph-powered",
    ],
)
def test_compat_endpoints_use_multiagent_runtime_and_not_legacy(
    endpoint: str,
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _boom(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("legacy answer_adaptive must not be called")

    monkeypatch.setattr(legacy_adaptive, "answer_question_adaptive", _boom, raising=True)

    response = client.post(
        endpoint,
        headers={"X-API-Key": "test-key-001"},
        json={"query": "compat endpoint"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"].startswith("multiagent:")
    assert payload["metadata"]["runtime"] == "multiagent"


def test_streaming_endpoint_does_not_call_legacy_answer_adaptive(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _boom(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("legacy answer_adaptive must not be called")

    monkeypatch.setattr(legacy_adaptive, "answer_question_adaptive", _boom, raising=True)
    monkeypatch.setattr(routes.config, "ENABLE_STREAMING", True, raising=False)

    response = client.post(
        "/api/v1/questions/adaptive-stream",
        headers={"X-API-Key": "test-key-001"},
        json={"query": "stream check"},
    )
    assert response.status_code == 200

    events = _collect_sse_events(response.text)
    done_events = [event for event in events if event["data"].get("done") is True]
    assert len(done_events) == 1
    assert done_events[0]["data"]["answer"].startswith("multiagent:")
    assert "legacy answer_adaptive must not be called" not in response.text
