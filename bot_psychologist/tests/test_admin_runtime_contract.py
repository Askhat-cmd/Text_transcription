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


def test_runtime_effective_multiagent_only_contract(admin_client):
    response = admin_client.get("/api/admin/runtime/effective", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    payload = response.json()

    assert payload["active_runtime"] == "multiagent"
    assert payload["runtime_entrypoint"] in {"multiagent_adapter", "answer_adaptive_deprecated_shim"}
    assert payload["pipeline_mode"] == "multiagent_only"
    assert payload["pipeline_mode_read_only"] is True
    assert payload["pipeline_mode_legacy_value"] is None
    assert payload["legacy_modes_selectable"] is False

    legacy = payload["legacy"]
    assert legacy["fallback_enabled"] is False
    assert legacy["fallback_used"] is False
    assert legacy["cascade_available"] is True
    assert legacy["cascade_status"] == "deprecated_retained_for_purge"
    assert legacy["purge_planned_prd"] == "PRD-041"

    assert payload["compatibility"]["pipeline_mode"] == "multiagent_only"
    assert payload["compatibility"]["legacy_modes_selectable"] is False
    assert payload["compatibility"]["pipeline_mode_read_only"] is True

    thread_manager = payload["agents"]["thread_manager"]
    assert thread_manager["kind"] == "heuristic"
    assert thread_manager["llm_model_effective"] is False

    assert payload["pipeline_mode"] not in {"legacy_adaptive", "hybrid"}


def test_orchestrator_mode_endpoint_rejects_legacy_and_normalizes_alias(admin_client):
    rejected_legacy = admin_client.patch(
        "/api/admin/orchestrator/config",
        headers=ADMIN_HEADERS,
        json={"pipeline_mode": "legacy_adaptive"},
    )
    assert rejected_legacy.status_code == 422

    rejected_hybrid = admin_client.patch(
        "/api/admin/orchestrator/config",
        headers=ADMIN_HEADERS,
        json={"pipeline_mode": "hybrid"},
    )
    assert rejected_hybrid.status_code == 422

    accepted_alias = admin_client.patch(
        "/api/admin/orchestrator/config",
        headers=ADMIN_HEADERS,
        json={"pipeline_mode": "full_multiagent"},
    )
    assert accepted_alias.status_code == 200
    accepted_payload = accepted_alias.json()
    assert accepted_payload["pipeline_mode"] == "multiagent_only"
    assert accepted_payload["pipeline_mode_read_only"] is True


def test_thread_manager_llm_contract_exposed(admin_client):
    response = admin_client.get("/api/admin/agents/llm-config", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    payload = response.json()
    thread_manager = payload["agents"]["thread_manager"]
    assert thread_manager["kind"] == "heuristic"
    assert thread_manager["llm_model_effective"] is False
