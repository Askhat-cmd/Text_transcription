from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api import routes
from api.dependencies import get_data_loader, get_graph_client, get_retriever
from api.main import app


def _extract_done_payload(sse_text: str) -> dict:
    for event in reversed([chunk for chunk in sse_text.split("\n\n") if chunk.strip()]):
        for line in event.splitlines():
            if not line.startswith("data:"):
                continue
            payload = json.loads(line.replace("data:", "", 1).strip())
            if payload.get("done") is True:
                return payload
    raise AssertionError("SSE done payload not found")


def _stub_adaptive_result(*_args, **_kwargs):
    return {
        "status": "success",
        "answer": "ok",
        "state_analysis": {
            "primary_state": "curious",
            "confidence": 0.9,
            "emotional_tone": "calm",
            "recommendations": [],
        },
        "path_recommendation": None,
        "feedback_prompt": "",
        "concepts": [],
        "sources": [],
        "conversation_context": "",
        "metadata": {
            "recommended_mode": "PRESENCE",
            "decision_rule_id": 10,
            "confidence_level": "medium",
            "confidence_score": 0.8,
            "user_level": "advanced",
            "user_level_adapter_applied": False,
        },
        "debug_trace": {
            "user_level": "advanced",
            "user_level_adapter_applied": False,
            "llm_calls": [],
        },
        "processing_time_seconds": 0.01,
    }


def test_no_user_level_fields_in_adaptive_metadata_and_stream_trace(monkeypatch) -> None:
    monkeypatch.setattr(routes, "answer_question_adaptive", _stub_adaptive_result)
    monkeypatch.setattr(routes.config, "ENABLE_STREAMING", True, raising=False)

    app.dependency_overrides[get_data_loader] = lambda: object()
    app.dependency_overrides[get_graph_client] = lambda: object()
    app.dependency_overrides[get_retriever] = lambda: object()

    try:
        with TestClient(app, base_url="http://localhost") as client:
            adaptive = client.post(
                "/api/v1/questions/adaptive",
                headers={"X-API-Key": "dev-key-001"},
                json={"query": "test", "user_id": "u1", "debug": True},
            )
            stream = client.post(
                "/api/v1/questions/adaptive-stream",
                headers={"X-API-Key": "dev-key-001"},
                json={"query": "test", "user_id": "u1"},
            )
    finally:
        app.dependency_overrides.clear()

    assert adaptive.status_code == 200
    metadata = adaptive.json()["metadata"]
    assert "user_level" not in metadata
    assert "user_level_adapter_applied" not in metadata

    done = _extract_done_payload(stream.text)
    assert done["done"] is True
    trace = done.get("trace") or {}
    assert "user_level" not in trace
    assert "user_level_adapter_applied" not in trace
