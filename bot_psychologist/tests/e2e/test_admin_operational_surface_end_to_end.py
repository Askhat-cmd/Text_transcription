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
        "surface-session",
        {
            "turn_number": 2,
            "hybrid_query_preview": "explain neo bot architecture",
            "diagnostics_v1": {
                "interaction_mode": "curious",
                "nervous_system_state": "window",
                "request_function": "understand",
                "core_theme": "architecture",
            },
            "resolved_route": "inform",
            "prompt_stack_v2": {
                "enabled": True,
                "version": "2.0",
                "order": ["AA_SAFETY", "CORE_IDENTITY"],
                "sections": {"AA_SAFETY": 120, "CORE_IDENTITY": 240},
            },
            "output_validation": {"passed": True, "warnings": []},
            "blocks_initial": 9,
            "blocks_after_cap": 3,
        },
    )

    with TestClient(app, base_url="http://localhost") as client:
        yield client


def test_admin_operational_surface_end_to_end(admin_client):
    runtime = admin_client.get("/api/admin/runtime/effective", headers=ADMIN_HEADERS)
    diagnostics = admin_client.get("/api/admin/diagnostics/effective", headers=ADMIN_HEADERS)
    trace_last = admin_client.get("/api/admin/trace/last", headers=ADMIN_HEADERS)
    trace_recent = admin_client.get("/api/admin/trace/recent?limit=5", headers=ADMIN_HEADERS)
    prompt_usage = admin_client.get("/api/admin/prompts/stack-v2/usage", headers=ADMIN_HEADERS)

    assert runtime.status_code == 200
    assert diagnostics.status_code == 200
    assert trace_last.status_code == 200
    assert trace_recent.status_code == 200
    assert prompt_usage.status_code == 200

    runtime_payload = runtime.json()
    assert runtime_payload["schema_version"] == "10.4.1"
    assert "feature_flags" in runtime_payload
    assert "trace" in runtime_payload

    diagnostics_payload = diagnostics.json()
    assert diagnostics_payload["contract"] == "diagnostics-v1"
    assert diagnostics_payload["trace_available"] is False
    assert diagnostics_payload["last_snapshot"] == {}

    last_payload = trace_last.json()
    assert last_payload["available"] is True
    assert last_payload["trace"]["routing"]["resolved_route"] == "inform"

    recent_payload = trace_recent.json()
    assert recent_payload["available"] is True
    assert recent_payload["count"] >= 1

    prompt_payload = prompt_usage.json()
    assert prompt_payload["last_turn_available"] is True
    assert "CORE_IDENTITY" in set(prompt_payload["last_turn"]["used_sections"])
