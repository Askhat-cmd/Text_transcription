from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from api.main import app
from api.session_store import get_session_store
from bot_agent.config import config
from bot_agent.runtime_config import RuntimeConfig


ADMIN_HEADERS = {"X-API-Key": "dev-key-001"}


@pytest.fixture()
def admin_client(tmp_path, monkeypatch):
    override_path = tmp_path / "admin_overrides.json"
    monkeypatch.setattr(RuntimeConfig, "OVERRIDES_PATH", override_path, raising=False)
    monkeypatch.setattr(RuntimeConfig, "_cache_mtime", 0.0, raising=False)
    monkeypatch.setattr(RuntimeConfig, "_cache", {}, raising=False)
    monkeypatch.setattr(config, "OVERRIDES_PATH", override_path, raising=False)
    monkeypatch.setattr(config, "WARMUP_ON_START", False, raising=False)

    store = get_session_store()
    monkeypatch.setattr(store, "_sessions", {}, raising=False)
    monkeypatch.setattr(store, "_blobs", {}, raising=False)
    for idx in range(1, 4):
        store.append_trace(
            "trace-session",
            {
                "turn_number": idx,
                "hybrid_query_preview": f"question-{idx}",
                "diagnostics_v1": {"interaction_mode": "curious"},
                "resolved_route": "reflect",
                "recommended_mode": "PRESENCE",
                "confidence_score": 0.66,
                "confidence_level": "medium",
                "decision_rule_id": "rule-neo-1",
                "blocks_initial": 9,
                "blocks_after_cap": 3,
                "block_cap": 3,
                "reranker_enabled": True,
                "config_snapshot": {"VOYAGE_TOP_K": 5},
                "chunks_retrieved": [{"id": "a"}, {"id": "b"}],
                "chunks_after_filter": [{"id": "a"}],
                "prompt_stack_v2": {
                    "enabled": True,
                    "version": "2.0",
                    "order": ["AA_SAFETY", "CORE_IDENTITY"],
                    "sections": {"AA_SAFETY": 100, "CORE_IDENTITY": 200},
                },
                "output_validation": {"passed": True, "anti_sparse_triggered": False},
                "summary_used": True,
                "summary_length": 120,
                "context_written": "snapshot ok",
                "semantic_hits": 2,
                "memory_strategy": "summary_first",
                "anomalies": [],
            },
        )

    with TestClient(app, base_url="http://localhost") as client:
        yield client


def test_admin_trace_last_payload_shape(admin_client):
    response = admin_client.get("/api/v1/admin/trace/last", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_version"] == "10.4.1"
    assert payload["available"] is True
    trace = payload["trace"]
    assert "diagnostics" in trace
    assert "routing" in trace
    assert "retrieval" in trace
    assert "prompt_stack" in trace
    assert "validation" in trace
    assert "memory" in trace
    assert "flags" in trace
    assert "anomalies" in trace


def test_admin_trace_recent_payload_shape(admin_client):
    response = admin_client.get("/api/v1/admin/trace/recent?limit=2", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_version"] == "10.4.1"
    assert payload["available"] is True
    assert payload["count"] == 2
    assert len(payload["traces"]) == 2
    assert payload["traces"][-1]["turn_number"] == 3

