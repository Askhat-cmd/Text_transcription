from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from api.main import app
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
    assert trace_last.status_code in {404, 410}
    assert trace_recent.status_code in {404, 410}
    assert prompt_usage.status_code in {404, 410}

    runtime_payload = runtime.json()
    assert runtime_payload["schema_version"] == "10.5.1"
    assert "feature_flags" in runtime_payload
    assert "trace" in runtime_payload
    assert runtime_payload["trace"]["developer_trace_supported"] is True

    diagnostics_payload = diagnostics.json()
    assert diagnostics_payload["contract"] == "diagnostics-v1"
    assert diagnostics_payload["trace_available"] is False
    assert diagnostics_payload["last_snapshot"] == {}
