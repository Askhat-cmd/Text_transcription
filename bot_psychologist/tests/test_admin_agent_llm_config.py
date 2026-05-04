"""Admin API tests for per-agent LLM config endpoints."""

from fastapi.testclient import TestClient
import pytest

from api.main import app
from bot_agent.config import config
from bot_agent.multiagent.agents.agent_llm_config import (
    _AGENT_MODEL_OVERRIDES,
    _AGENT_TEMPERATURE_OVERRIDES,
)
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


@pytest.fixture(autouse=True)
def clear_overrides():
    _AGENT_MODEL_OVERRIDES.clear()
    _AGENT_TEMPERATURE_OVERRIDES.clear()
    yield
    _AGENT_MODEL_OVERRIDES.clear()
    _AGENT_TEMPERATURE_OVERRIDES.clear()


def test_get_llm_config(admin_client):
    res = admin_client.get("/api/admin/agents/llm-config", headers=ADMIN_HEADERS)
    assert res.status_code == 200
    data = res.json()
    assert set(data["agents"].keys()) == {"state_analyzer", "thread_manager", "writer"}
    assert data["agents"]["state_analyzer"]["model"] == "gpt-5-nano"
    assert data["agents"]["thread_manager"]["model"] == "gpt-5-nano"
    assert data["agents"]["writer"]["model"] == "gpt-5-mini"
    assert data["agents"]["writer"]["temperature"] == pytest.approx(0.7)
    assert data["agents"]["state_analyzer"]["temperature"] == pytest.approx(0.1)


def test_get_llm_config_allowed_models(admin_client):
    res = admin_client.get("/api/admin/agents/llm-config", headers=ADMIN_HEADERS)
    assert res.status_code == 200
    models = res.json()["allowed_models"]
    assert "gpt-5-nano" in models
    assert "gpt-5-mini" in models


def test_patch_valid_model(admin_client):
    res = admin_client.patch(
        "/api/admin/agents/writer/llm-config",
        json={"model": "gpt-5"},
        headers=ADMIN_HEADERS,
    )
    assert res.status_code == 200
    assert res.json()["model"] == "gpt-5"

    get_res = admin_client.get("/api/admin/agents/llm-config", headers=ADMIN_HEADERS)
    payload = get_res.json()
    assert payload["agents"]["writer"]["model"] == "gpt-5"
    assert payload["agents"]["writer"]["is_overridden"] is True


def test_patch_invalid_model(admin_client):
    res = admin_client.patch(
        "/api/admin/agents/writer/llm-config",
        json={"model": "claude-3-opus"},
        headers=ADMIN_HEADERS,
    )
    assert res.status_code == 422
    assert "not allowed" in res.json()["detail"]


def test_patch_unknown_agent(admin_client):
    res = admin_client.patch(
        "/api/admin/agents/fake_agent/llm-config",
        json={"model": "gpt-5-nano"},
        headers=ADMIN_HEADERS,
    )
    assert res.status_code == 422


def test_patch_missing_model_field(admin_client):
    res = admin_client.patch(
        "/api/admin/agents/writer/llm-config",
        json={},
        headers=ADMIN_HEADERS,
    )
    assert res.status_code == 422


def test_patch_temperature_only(admin_client):
    res = admin_client.patch(
        "/api/admin/agents/writer/llm-config",
        json={"temperature": 0.9},
        headers=ADMIN_HEADERS,
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload["temperature"] == pytest.approx(0.9)
    assert payload["is_temperature_overridden"] is True

    get_res = admin_client.get("/api/admin/agents/llm-config", headers=ADMIN_HEADERS)
    writer_cfg = get_res.json()["agents"]["writer"]
    assert writer_cfg["temperature"] == pytest.approx(0.9)
    assert writer_cfg["is_temperature_overridden"] is True


def test_reset_restores_default(admin_client):
    admin_client.patch(
        "/api/admin/agents/writer/llm-config",
        json={"model": "gpt-5", "temperature": 1.2},
        headers=ADMIN_HEADERS,
    )

    res = admin_client.post(
        "/api/admin/agents/writer/llm-config/reset",
        headers=ADMIN_HEADERS,
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload["is_overridden"] is False
    assert payload["is_temperature_overridden"] is False
    assert payload["model"] == "gpt-5-mini"
    assert payload["temperature"] == pytest.approx(0.7)

    get_res = admin_client.get("/api/admin/agents/llm-config", headers=ADMIN_HEADERS)
    assert get_res.json()["agents"]["writer"]["is_overridden"] is False
