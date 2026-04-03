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
        "sources": [
            {
                "block_id": "b1",
                "title": "source",
                "youtube_link": "",
                "start": 0,
                "end": 0,
                "block_type": "text",
                "complexity_score": 0.1,
            }
        ],
        "conversation_context": "ctx",
        "metadata": {
            "recommended_mode": "PRESENCE",
            "decision_rule_id": 10,
            "confidence_level": "medium",
            "confidence_score": 0.8,
            "sd_level": "GREEN",
        },
        "debug_trace": {
            "sd_classification": {
                "method": "fallback",
                "primary": "GREEN",
                "secondary": None,
                "confidence": 0.5,
                "indicator": "fallback",
                "allowed_levels": ["GREEN"],
            },
            "sd_detail": {
                "method": "fallback",
                "primary": "GREEN",
                "secondary": None,
                "confidence": 0.5,
                "indicator": "fallback",
                "allowed_levels": ["GREEN"],
            },
            "sd_level": "GREEN",
            "chunks_retrieved": [
                {
                    "block_id": "b1",
                    "title": "source",
                    "score": 0.1,
                    "passed_filter": True,
                    "preview": "x",
                }
            ],
            "chunks_after_filter": [],
            "llm_calls": [{"step": "answer", "model": "gpt-5-mini"}],
            "context_written": "ctx",
            "total_duration_ms": 10,
            "config_snapshot": {
                "conversation_history_depth": 8,
                "max_context_size": 2200,
                "semantic_search_top_k": 20,
                "sd_confidence_threshold": 0.65,
                "fast_path_enabled": True,
                "rerank_enabled": True,
                "model_name": "gpt-5-mini",
                "user_level": "advanced",
            },
        },
        "processing_time_seconds": 0.01,
    }


def test_trace_contract_after_purge(monkeypatch) -> None:
    monkeypatch.setenv("DISABLE_SD_RUNTIME", "true")
    monkeypatch.setattr(routes, "answer_question_adaptive", _stub_adaptive_result)

    app.dependency_overrides[get_data_loader] = lambda: object()
    app.dependency_overrides[get_graph_client] = lambda: object()
    app.dependency_overrides[get_retriever] = lambda: object()

    try:
        with TestClient(app, base_url="http://localhost") as client:
            response = client.post(
                "/api/v1/questions/adaptive",
                headers={"X-API-Key": "dev-key-001"},
                json={"query": "тест", "user_id": "u1", "debug": True},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    trace = response.json().get("trace")
    assert isinstance(trace, dict)
    assert "sd_classification" not in trace
    assert "sd_detail" not in trace
    assert "sd_level" not in trace
    cfg = trace.get("config_snapshot") or {}
    assert isinstance(cfg, dict)
    assert "user_level" not in cfg
    assert "sd_confidence_threshold" not in cfg
