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


def test_admin_schema_v105_management_only(admin_client) -> None:
    config_resp = admin_client.get("/api/v1/admin/config", headers=ADMIN_HEADERS)
    runtime_resp = admin_client.get("/api/v1/admin/runtime/effective", headers=ADMIN_HEADERS)
    diagnostics_resp = admin_client.get("/api/v1/admin/diagnostics/effective", headers=ADMIN_HEADERS)

    assert config_resp.status_code == 200
    assert runtime_resp.status_code == 200
    assert diagnostics_resp.status_code == 200

    runtime_payload = runtime_resp.json()
    assert runtime_payload["trace"] == {"available": runtime_payload["trace"]["available"]}
    assert "session_id" not in runtime_payload["trace"]
    assert "last_turn_number" not in runtime_payload["trace"]

    diagnostics_payload = diagnostics_resp.json()
    assert diagnostics_payload["last_snapshot"] == {}
    assert diagnostics_payload["trace_available"] is False
