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


def test_admin_config_schema_v104_exists_and_contains_markers(admin_client):
    response = admin_client.get("/api/v1/admin/config/schema-v104", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    payload = response.json()

    assert payload["schema_version"] == "10.5"
    assert "editable" in payload
    assert "read_only" in payload
    assert "deprecated" in payload

    editable_groups = payload["editable"]["groups"]
    assert "llm" in editable_groups
    assert "retrieval" in editable_groups
    assert "routing" in editable_groups

    routing_params = editable_groups["routing"]["params"]
    assert "DECISION_GATE_RULE_THRESHOLD" in routing_params
    assert routing_params["DECISION_GATE_RULE_THRESHOLD"]["deprecated"] is True
    assert routing_params["DECISION_GATE_RULE_THRESHOLD"]["compatibility_only"] is True

    assert "runtime_status" in payload["read_only"]
    assert "feature_flags" in payload["read_only"]
