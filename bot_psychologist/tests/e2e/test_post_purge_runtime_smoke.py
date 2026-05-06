from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from api import dependencies as deps
from api.main import app
import api.routes as routes
from bot_agent.config import config


TEST_HEADERS = {"X-API-Key": "test-key-001"}


def _stub_multiagent_runtime(*, query: str, user_id: str, **_kwargs: Any) -> dict[str, Any]:
    return {
        "status": "ok",
        "answer": f"multiagent:{query}",
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
        "metadata": {
            "runtime": "multiagent",
            "runtime_entrypoint": "multiagent_adapter",
            "legacy_fallback_used": False,
            "pipeline_version": "multiagent_v1",
            "runtime_user_scope": user_id,
        },
        "debug": {
            "multiagent_enabled": True,
            "pipeline_version": "multiagent_v1",
            "runtime_entrypoint": "multiagent_adapter",
            "legacy_fallback_used": False,
            "state_analyzer_fallback_used": False,
        },
        "debug_trace": {
            "session_id": user_id,
            "multiagent_enabled": True,
            "pipeline_version": "multiagent_v1",
            "writer_api_mode": "responses",
            "primary_model": "gpt-5-mini",
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
    monkeypatch.setattr(config, "BOT_DB_PATH", tmp_path / "post_purge_runtime_smoke.db", raising=False)
    monkeypatch.setattr(deps, "_identity_repository", None, raising=False)
    monkeypatch.setattr(deps, "_identity_service", None, raising=False)
    monkeypatch.setattr(deps, "_conversation_repository", None, raising=False)
    monkeypatch.setattr(deps, "_conversation_service", None, raising=False)
    monkeypatch.setattr(routes, "run_multiagent_adaptive_sync", _stub_multiagent_runtime, raising=True)
    monkeypatch.setattr(routes.config, "ENABLE_STREAMING", True, raising=False)
    with TestClient(app, base_url="http://localhost") as test_client:
        yield test_client


def test_post_purge_adaptive_runtime_smoke(client: TestClient) -> None:
    response = client.post(
        "/api/v1/questions/adaptive",
        headers=TEST_HEADERS,
        json={"query": "smoke", "session_id": "smoke-session"},
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["answer"]
    assert payload["metadata"]["runtime"] == "multiagent"
    assert payload["metadata"]["runtime_entrypoint"] == "multiagent_adapter"
    assert payload["metadata"]["legacy_fallback_used"] is False
    assert payload["metadata"]["pipeline_version"] == "multiagent_v1"


def test_post_purge_streaming_smoke(client: TestClient) -> None:
    response = client.post(
        "/api/v1/questions/adaptive-stream",
        headers=TEST_HEADERS,
        json={"query": "stream smoke", "session_id": "smoke-session"},
    )
    assert response.status_code == 200

    events = _collect_sse_events(response.text)
    done_events = [event for event in events if event["data"].get("done") is True]
    assert len(done_events) == 1
    assert done_events[0]["data"]["answer"].startswith("multiagent:")
