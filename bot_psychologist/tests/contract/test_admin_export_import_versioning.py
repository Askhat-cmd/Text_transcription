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


def test_admin_export_has_schema_version(admin_client):
    response = admin_client.get("/api/v1/admin/export", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    payload = response.json()
    assert "meta" in payload
    assert payload["meta"]["schema_version"] == "10.4"
    assert payload["meta"]["schema_family"] == "admin_overrides"


def test_admin_import_accepts_legacy_payload_and_maps_known_keys(admin_client):
    response = admin_client.post(
        "/api/v1/admin/import",
        headers=ADMIN_HEADERS,
        json={
            "config": {
                "RETRIEVAL_TOP_K": 6,  # legacy key -> TOP_K_BLOCKS
                "UNKNOWN_DEPRECATED_FIELD": True,  # should be safely ignored
            },
            "prompts": {
                "prompt_mode_informational": "legacy",
                "unknown_prompt_key": "ignored",
            },
            "history": [],
            "meta": {},  # no schema_version => legacy-v1
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_version"] == "10.4"
    assert payload["imported_schema_version"] == "legacy-v1"
    assert "UNKNOWN_DEPRECATED_FIELD" in payload["ignored_config_keys"]
    assert "unknown_prompt_key" in payload["ignored_prompt_keys"]

    exported = admin_client.get("/api/v1/admin/export", headers=ADMIN_HEADERS).json()
    assert exported["config"]["TOP_K_BLOCKS"] == 6
    assert "UNKNOWN_DEPRECATED_FIELD" not in exported["config"]
