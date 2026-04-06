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

    with TestClient(app, base_url="http://localhost") as client:
        yield client


def test_admin_runtime_effective_payload_shape(admin_client):
    response = admin_client.get("/api/v1/admin/runtime/effective", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    payload = response.json()

    assert payload["schema_version"] == "10.4.1"
    assert payload["admin_schema_version"] == "10.4"
    assert "prompt_stack_version" in payload

    assert "status" in payload
    assert "feature_flags" in payload
    assert "all" in payload["feature_flags"]
    assert "groups" in payload["feature_flags"]
    assert "diagnostics" in payload
    assert "routing" in payload
    assert "validation" in payload
    assert "trace" in payload

    assert "config_validation_status" in payload["validation"]
    assert isinstance(payload["validation"]["config_validation_status"]["valid"], bool)
    assert isinstance(payload["validation"]["config_validation_status"]["errors"], list)

