from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

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
        yield client, override_path


def test_get_config_schema_has_groups(admin_client):
    client, _ = admin_client
    res = client.get("/api/v1/admin/config/schema", headers=ADMIN_HEADERS)
    assert res.status_code == 200
    schema = res.json()
    assert "llm" in schema
    assert "retrieval" in schema
    assert "routing" in schema
    assert "MAX_TOKENS" in schema["llm"]
    assert "FREE_CONVERSATION_MODE" in schema["routing"]


def test_post_grouped_config_updates_runtime(admin_client):
    client, override_path = admin_client
    res = client.post(
        "/api/v1/admin/config",
        headers=ADMIN_HEADERS,
        json={"routing": {"FREE_CONVERSATION_MODE": True}, "llm": {"MAX_TOKENS_SOFT_CAP": 4096}},
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload["updated"]["FREE_CONVERSATION_MODE"] is True
    assert payload["updated"]["MAX_TOKENS_SOFT_CAP"] == 4096
    assert config.FREE_CONVERSATION_MODE is True
    assert config.MAX_TOKENS_SOFT_CAP == 4096

    data = json.loads(Path(override_path).read_text(encoding="utf-8"))
    assert data["config"]["FREE_CONVERSATION_MODE"] is True
    assert data["config"]["MAX_TOKENS_SOFT_CAP"] == 4096


def test_post_grouped_config_sets_null_max_tokens(admin_client):
    client, _ = admin_client
    res = client.post(
        "/api/v1/admin/config",
        headers=ADMIN_HEADERS,
        json={"llm": {"MAX_TOKENS": None}},
    )
    assert res.status_code == 200
    assert "MAX_TOKENS" in res.json()["updated"]
    assert config.MAX_TOKENS is None


def test_status_has_required_fields(admin_client):
    client, _ = admin_client
    res = client.get("/api/v1/admin/status", headers=ADMIN_HEADERS)
    assert res.status_code == 200
    payload = res.json()
    assert {"degraded_mode", "data_source", "blocks_loaded", "version"} <= set(payload.keys())


def test_reload_data_calls_loader(admin_client):
    client, _ = admin_client
    with patch("api.admin_routes.data_loader.reload", return_value=[]) as mock_reload:
        res = client.post("/api/v1/admin/reload-data", headers=ADMIN_HEADERS)
    assert res.status_code == 200
    mock_reload.assert_called_once()


def test_prompts_endpoints_roundtrip(admin_client):
    client, _ = admin_client
    list_res = client.get("/api/v1/admin/prompts", headers=ADMIN_HEADERS)
    assert list_res.status_code == 200
    names = [item["name"] for item in list_res.json()]
    assert "prompt_system_base" in names

    get_res = client.get("/api/v1/admin/prompts/prompt_system_base", headers=ADMIN_HEADERS)
    assert get_res.status_code == 200
    original = get_res.json()["content"]
    assert original

    new_content = "# Test\nСвободный развёрнутый ответ."
    put_res = client.put(
        "/api/v1/admin/prompts/prompt_system_base",
        headers=ADMIN_HEADERS,
        json={"content": new_content},
    )
    assert put_res.status_code == 200

    changed = client.get("/api/v1/admin/prompts/prompt_system_base", headers=ADMIN_HEADERS).json()["content"]
    assert changed == new_content

    reset_res = client.post("/api/v1/admin/prompts/prompt_system_base/reset", headers=ADMIN_HEADERS)
    assert reset_res.status_code == 200
    restored = client.get("/api/v1/admin/prompts/prompt_system_base", headers=ADMIN_HEADERS).json()["content"]
    assert restored != new_content
