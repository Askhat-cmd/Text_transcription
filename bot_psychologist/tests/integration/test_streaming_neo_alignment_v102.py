from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.main import app
from api import routes


def _extract_done_payload(sse_text: str) -> dict:
    events = [chunk for chunk in sse_text.split("\n\n") if chunk.strip()]
    for event in reversed(events):
        for line in event.splitlines():
            if not line.startswith("data:"):
                continue
            payload = json.loads(line.replace("data:", "", 1).strip())
            if payload.get("done") is True:
                return payload
    raise AssertionError("SSE done payload not found")


def _result_for_mode(mode: str) -> dict:
    return {
        "status": "success",
        "answer": "тестовый ответ",
        "state_analysis": {
            "primary_state": "curious",
            "confidence": 0.9,
            "emotional_tone": "neutral",
            "recommendations": [],
        },
        "path_recommendation": None,
        "feedback_prompt": "",
        "concepts": [],
        "sources": [],
        "conversation_context": "",
        "metadata": {
            "recommended_mode": mode,
            "decision_rule_id": 10,
            "confidence_level": "medium",
            "confidence_score": 0.5,
        },
        "processing_time_seconds": 0.01,
    }


def test_streaming_forwards_include_path_flag_to_same_runtime(monkeypatch) -> None:
    captured: list[bool] = []

    def _fake_answer(*_args, **kwargs):
        captured.append(bool(kwargs.get("include_path_recommendation")))
        return _result_for_mode("PRESENCE")

    monkeypatch.setattr(routes, "answer_question_adaptive", _fake_answer)
    monkeypatch.setattr(routes.config, "ENABLE_STREAMING", True, raising=False)

    with TestClient(app, base_url="http://localhost") as client:
        response = client.post(
            "/api/v1/questions/adaptive-stream",
            headers={"X-API-Key": "test-key-001"},
            json={"query": "тест", "user_id": "u1", "include_path": True},
        )

    assert response.status_code == 200
    assert captured == [True]


def test_streaming_mode_matches_adaptive_mode_contract(monkeypatch) -> None:
    def _fake_answer(*_args, **_kwargs):
        return _result_for_mode("INFORMATIONAL")

    monkeypatch.setattr(routes, "answer_question_adaptive", _fake_answer)
    monkeypatch.setattr(routes.config, "ENABLE_STREAMING", True, raising=False)

    payload = {"query": "что такое осознанность?", "user_id": "u1"}

    with TestClient(app, base_url="http://localhost") as client:
        adaptive = client.post(
            "/api/v1/questions/adaptive",
            headers={"X-API-Key": "test-key-001"},
            json=payload,
        )
        stream = client.post(
            "/api/v1/questions/adaptive-stream",
            headers={"X-API-Key": "test-key-001"},
            json=payload,
        )

    assert adaptive.status_code == 200
    assert stream.status_code == 200
    adaptive_mode = (adaptive.json().get("metadata") or {}).get("recommended_mode")
    stream_mode = _extract_done_payload(stream.text).get("mode")
    assert adaptive_mode == "INFORMATIONAL"
    assert stream_mode == adaptive_mode
