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


def test_agents_status_returns_5_agents(admin_client):
    resp = admin_client.get("/api/admin/agents/status", headers=ADMIN_HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["agents"]) == 5
    assert {item["id"] for item in data["agents"]} == {
        "state_analyzer", "thread_manager", "memory_retrieval", "writer", "validator"
    }


def test_agent_toggle(admin_client):
    resp = admin_client.post(
        "/api/admin/agents/writer/toggle",
        json={"enabled": False},
        headers=ADMIN_HEADERS,
    )
    assert resp.status_code == 200
    assert resp.json()["enabled"] is False

    restore = admin_client.post(
        "/api/admin/agents/writer/toggle",
        json={"enabled": True},
        headers=ADMIN_HEADERS,
    )
    assert restore.status_code == 200
    assert restore.json()["enabled"] is True


def test_agent_toggle_unknown(admin_client):
    resp = admin_client.post(
        "/api/admin/agents/ghost/toggle",
        json={"enabled": False},
        headers=ADMIN_HEADERS,
    )
    assert resp.status_code == 404


def test_orchestrator_get(admin_client):
    resp = admin_client.get("/api/admin/orchestrator/config", headers=ADMIN_HEADERS)
    assert resp.status_code == 200
    assert resp.json()["pipeline_mode"] in {"full_multiagent", "hybrid", "legacy_adaptive"}


@pytest.mark.parametrize("mode", ["full_multiagent", "hybrid", "legacy_adaptive"])
def test_orchestrator_patch_valid(admin_client, mode: str):
    resp = admin_client.patch(
        "/api/admin/orchestrator/config",
        json={"pipeline_mode": mode},
        headers=ADMIN_HEADERS,
    )
    assert resp.status_code == 200
    assert resp.json()["pipeline_mode"] == mode


def test_orchestrator_patch_invalid(admin_client):
    resp = admin_client.patch(
        "/api/admin/orchestrator/config",
        json={"pipeline_mode": "turbo_mode"},
        headers=ADMIN_HEADERS,
    )
    assert resp.status_code == 422


def test_traces_empty(admin_client):
    resp = admin_client.get("/api/admin/agents/traces", headers=ADMIN_HEADERS)
    assert resp.status_code == 200
    assert isinstance(resp.json()["traces"], list)


def test_traces_record_and_fetch(admin_client):
    rec = admin_client.post(
        "/api/admin/agents/traces/record",
        json={"agent_id": "writer", "request_id": "r1", "user_id": "u1", "latency_ms": 500},
        headers=ADMIN_HEADERS,
    )
    assert rec.status_code == 200

    resp = admin_client.get("/api/admin/agents/traces?agent_id=writer", headers=ADMIN_HEADERS)
    assert resp.status_code == 200
    assert any(item["agent_id"] == "writer" for item in resp.json()["traces"])


def test_threads_list(admin_client):
    resp = admin_client.get("/api/admin/threads", headers=ADMIN_HEADERS)
    assert resp.status_code == 200
    assert "threads" in resp.json()


def test_threads_delete_nonexistent(admin_client):
    resp = admin_client.delete("/api/admin/threads/ghost_user_xyz999", headers=ADMIN_HEADERS)
    assert resp.status_code == 404


def test_agent_prompts_writer(admin_client):
    resp = admin_client.get("/api/admin/agents/writer/prompts", headers=ADMIN_HEADERS)
    assert resp.status_code == 200
    assert resp.json()["agent_id"] == "writer"


def test_agent_prompts_unknown(admin_client):
    resp = admin_client.get("/api/admin/agents/ghost/prompts", headers=ADMIN_HEADERS)
    assert resp.status_code == 404


def test_auth_required_on_multiagent_endpoints(admin_client):
    for method, url in [
        ("GET", "/api/admin/agents/status"),
        ("GET", "/api/admin/orchestrator/config"),
        ("GET", "/api/admin/agents/traces"),
        ("GET", "/api/admin/threads"),
    ]:
        resp = admin_client.request(method, url)
        assert resp.status_code in {401, 403, 422}, f"{method} {url} should require auth"
