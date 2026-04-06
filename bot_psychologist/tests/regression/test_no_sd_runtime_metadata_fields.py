from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api import routes
from api.dependencies import get_data_loader, get_graph_client, get_retriever
from api.main import app


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
            "sd_level": "GREEN",
            "sd_secondary": "YELLOW",
            "sd_confidence": 0.6,
            "sd_method": "fallback",
            "sd_allowed_blocks": ["GREEN"],
        },
        "processing_time_seconds": 0.01,
    }


def test_no_sd_runtime_metadata_fields_when_sd_disabled(monkeypatch) -> None:
    monkeypatch.setenv("DISABLE_SD_RUNTIME", "true")
    monkeypatch.setattr(routes, "answer_question_adaptive", _stub_adaptive_result)

    app.dependency_overrides[get_data_loader] = lambda: object()
    app.dependency_overrides[get_graph_client] = lambda: object()
    app.dependency_overrides[get_retriever] = lambda: object()

    try:
        with TestClient(app, base_url="http://localhost") as client:
            response = client.post(
                "/api/v1/questions/adaptive",
                headers={"X-API-Key": "test-key-001"},
                json={"query": "test", "user_id": "u1"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    metadata = response.json()["metadata"]
    for key in ("sd_level", "sd_secondary", "sd_confidence", "sd_method", "sd_allowed_blocks"):
        assert key not in metadata
    for key in ("decision_rule_id", "mode_reason", "confidence_level", "confidence_score"):
        assert key not in metadata
