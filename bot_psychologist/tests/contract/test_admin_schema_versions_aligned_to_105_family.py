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


def test_admin_schema_versions_aligned_to_105_family(admin_client) -> None:
    runtime = admin_client.get("/api/v1/admin/runtime/effective", headers=ADMIN_HEADERS)
    diagnostics = admin_client.get("/api/v1/admin/diagnostics/effective", headers=ADMIN_HEADERS)
    config_schema = admin_client.get("/api/v1/admin/config/schema-v104", headers=ADMIN_HEADERS)

    assert runtime.status_code == 200
    assert diagnostics.status_code == 200
    assert config_schema.status_code == 200

    assert runtime.json()["schema_version"] == "10.5.1"
    assert runtime.json()["admin_schema_version"] == "10.5"
    assert diagnostics.json()["schema_version"] == "10.5.1"
    assert config_schema.json()["schema_version"] == "10.5"

