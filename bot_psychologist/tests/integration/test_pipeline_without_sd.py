from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from api import routes
from api.dependencies import get_data_loader, get_graph_client, get_retriever
from api.main import app


def test_pipeline_without_sd_fields_still_returns_response(monkeypatch) -> None:
    monkeypatch.setenv("DISABLE_SD_RUNTIME", "true")

    def _stub_answer(*_args, **_kwargs):
        return {
            "status": "success",
            "answer": "stub answer",
            "state_analysis": {
                "primary_state": "curious",
                "confidence": 0.82,
                "emotional_tone": "calm",
                "recommendations": [],
            },
            "metadata": {
                "recommended_mode": "PRESENCE",
                "confidence_level": "medium",
                "confidence_score": 0.82,
            },
            "sources": [],
            "processing_time_seconds": 0.01,
        }

    monkeypatch.setattr(routes, "answer_question_adaptive", _stub_answer)

    app.dependency_overrides[get_data_loader] = lambda: object()
    app.dependency_overrides[get_graph_client] = lambda: object()
    app.dependency_overrides[get_retriever] = lambda: object()

    try:
        client = TestClient(app, base_url="http://localhost")
        response = client.post(
            "/api/v1/questions/adaptive",
            headers={"X-API-Key": "test-key-001"},
            json={
                "query": "проверь адаптивный ответ",
                "user_id": "phase1-test-user",
                "debug": False,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["answer"] == "stub answer"
    assert body["state_analysis"]["primary_state"] == "curious"
