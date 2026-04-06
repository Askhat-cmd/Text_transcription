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
    store.append_trace(
        "viewer-session",
        {
            "turn_number": 1,
            "hybrid_query_preview": "what is neo mindbot",
            "diagnostics_v1": {"interaction_mode": "curious"},
            "resolved_route": "inform",
            "blocks_initial": 8,
            "blocks_after_cap": 3,
            "prompt_stack_v2": {
                "enabled": True,
                "version": "2.0",
                "order": ["AA_SAFETY", "CORE_IDENTITY"],
                "sections": {"AA_SAFETY": 120, "CORE_IDENTITY": 220},
            },
            "output_validation": {"passed": True},
            "anomalies": [],
        },
    )

    with TestClient(app, base_url="http://localhost") as client:
        yield client


def test_admin_trace_viewer_last_turn_flow(admin_client):
    last_trace = admin_client.get("/api/admin/trace/last", headers=ADMIN_HEADERS)
    assert last_trace.status_code == 200
    payload = last_trace.json()
    assert payload["available"] is True
    assert payload["trace"]["turn_number"] == 1
    assert payload["trace"]["routing"]["resolved_route"] == "inform"

    recent = admin_client.get("/api/admin/trace/recent?limit=5", headers=ADMIN_HEADERS)
    assert recent.status_code == 200
    recent_payload = recent.json()
    assert recent_payload["available"] is True
    assert recent_payload["count"] >= 1
    assert recent_payload["traces"][0]["prompt_stack"]["enabled"] is True

