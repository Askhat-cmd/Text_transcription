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


def test_legacy_admin_payload_unknown_fields_do_not_break_import(admin_client):
    response = admin_client.post(
        "/api/admin/import",
        headers=ADMIN_HEADERS,
        json={
            "config": {
                "RETRIEVAL_TOP_K": 5,
                "DEPRECATED_OR_UNKNOWN_KEY": 123,
            },
            "prompts": {
                "unknown_prompt_name": "noop",
            },
            "history": [],
            "meta": {"schema_version": "9.9"},
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["imported_schema_version"] == "9.9"
    assert "DEPRECATED_OR_UNKNOWN_KEY" in payload["ignored_config_keys"]
    assert "unknown_prompt_name" in payload["ignored_prompt_keys"]

    exported = admin_client.get("/api/admin/export", headers=ADMIN_HEADERS).json()
    assert exported["config"]["TOP_K_BLOCKS"] == 5
    assert "DEPRECATED_OR_UNKNOWN_KEY" not in exported["config"]
    assert "unknown_prompt_name" not in exported["prompts"]
