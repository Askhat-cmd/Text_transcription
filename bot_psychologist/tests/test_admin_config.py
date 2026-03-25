"""
Tests for Admin Config hot-reload and persistence (PRD v0.6.0 Block 1).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import app
from bot_agent.config import config
from bot_agent.runtime_config import RuntimeConfig


DEV_HEADERS = {"X-API-Key": "dev-key-001"}


@pytest.fixture()
def admin_client(tmp_path, monkeypatch):
    override_path = tmp_path / "admin_overrides.json"

    # Redirect overrides to temp file and reset cache
    monkeypatch.setattr(RuntimeConfig, "OVERRIDES_PATH", override_path, raising=False)
    monkeypatch.setattr(RuntimeConfig, "_cache_mtime", 0.0, raising=False)
    monkeypatch.setattr(RuntimeConfig, "_cache", {}, raising=False)
    monkeypatch.setattr(config, "OVERRIDES_PATH", override_path, raising=False)

    # Disable warmup to keep tests fast
    monkeypatch.setattr(config, "WARMUP_ON_START", False, raising=False)

    with TestClient(app, base_url="http://localhost") as client:
        yield client, override_path


def _get_param_value(config_payload: dict, key: str) -> int:
    groups = config_payload.get("groups", {})
    for group in groups.values():
        params = group.get("params", {})
        if key in params:
            return int(params[key].get("value"))
    raise AssertionError(f"Config key not found in response: {key}")


def test_admin_config_hot_reload(admin_client):
    client, _override_path = admin_client

    res = client.get("/api/admin/config", headers=DEV_HEADERS)
    assert res.status_code == 200
    original_top_k = _get_param_value(res.json(), "TOP_K_BLOCKS")

    res = client.put(
        "/api/admin/config",
        headers=DEV_HEADERS,
        json={"key": "TOP_K_BLOCKS", "value": 7},
    )
    assert res.status_code == 200
    assert res.json()["value"] == 7
    assert res.json()["is_overridden"] is True

    # Ensure runtime config reflects updated value
    assert int(config.TOP_K_BLOCKS) == 7

    # Verify via GET
    res = client.get("/api/admin/config", headers=DEV_HEADERS)
    assert res.status_code == 200
    assert _get_param_value(res.json(), "TOP_K_BLOCKS") == 7

    # Reset back
    res = client.delete("/api/admin/config/TOP_K_BLOCKS", headers=DEV_HEADERS)
    assert res.status_code == 200
    assert int(config.TOP_K_BLOCKS) == original_top_k


def test_config_persists_after_reload(admin_client):
    client, override_path = admin_client

    res = client.put(
        "/api/admin/config",
        headers=DEV_HEADERS,
        json={"key": "TOP_K_BLOCKS", "value": 6},
    )
    assert res.status_code == 200

    assert override_path.exists()
    data = json.loads(Path(override_path).read_text(encoding="utf-8"))
    assert data.get("config", {}).get("TOP_K_BLOCKS") == 6

    # Simulate new RuntimeConfig instance reading persisted overrides
    RuntimeConfig._cache_mtime = 0.0
    RuntimeConfig._cache = {}
    fresh = RuntimeConfig()
    assert int(fresh.TOP_K_BLOCKS) == 6
