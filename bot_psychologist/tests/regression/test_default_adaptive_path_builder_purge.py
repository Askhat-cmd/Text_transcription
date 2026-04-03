from __future__ import annotations

import inspect
import sys
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.main import app
from api import routes
from api.models import AskQuestionRequest
from bot_agent import answer_adaptive


def _minimal_result() -> dict:
    return {
        "status": "success",
        "answer": "ok",
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
            "recommended_mode": "PRESENCE",
            "decision_rule_id": 10,
            "confidence_level": "medium",
            "confidence_score": 0.5,
        },
        "processing_time_seconds": 0.01,
    }


def test_request_model_include_path_default_is_false() -> None:
    request = AskQuestionRequest(query="что делать?")
    assert request.include_path is False


def test_answer_adaptive_signature_include_path_default_is_false() -> None:
    signature = inspect.signature(answer_adaptive.answer_question_adaptive)
    assert signature.parameters["include_path_recommendation"].default is False


def test_adaptive_endpoint_passes_include_path_false_by_default(monkeypatch) -> None:
    captured: list[bool] = []

    def _fake_answer_question_adaptive(*_args, **kwargs):
        captured.append(bool(kwargs.get("include_path_recommendation")))
        return _minimal_result()

    monkeypatch.setattr(routes, "answer_question_adaptive", _fake_answer_question_adaptive)

    with TestClient(app, base_url="http://localhost") as client:
        response = client.post(
            "/api/v1/questions/adaptive",
            headers={"X-API-Key": "test-key-001"},
            json={"query": "тест", "user_id": "u1"},
        )

    assert response.status_code == 200
    assert captured == [False]


def test_adaptive_endpoint_keeps_explicit_include_path_true(monkeypatch) -> None:
    captured: list[bool] = []

    def _fake_answer_question_adaptive(*_args, **kwargs):
        captured.append(bool(kwargs.get("include_path_recommendation")))
        return _minimal_result()

    monkeypatch.setattr(routes, "answer_question_adaptive", _fake_answer_question_adaptive)

    with TestClient(app, base_url="http://localhost") as client:
        response = client.post(
            "/api/v1/questions/adaptive",
            headers={"X-API-Key": "test-key-001"},
            json={"query": "тест", "user_id": "u1", "include_path": True},
        )

    assert response.status_code == 200
    assert captured == [True]
