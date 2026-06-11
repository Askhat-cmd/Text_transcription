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
    assert legacy["cascade_available"] is False
    assert legacy["cascade_status"] == "physically_removed"
    assert legacy["purge_planned_prd"] is None
    assert legacy["purge_completed_prd"] == "PRD-041"

    assert payload["compatibility"]["pipeline_mode"] == "multiagent_only"
    assert payload["compatibility"]["legacy_modes_selectable"] is False
    assert payload["compatibility"]["pipeline_mode_read_only"] is True
    assert payload["deprecated_runtime_flags"] == {
        "MULTIAGENT_ENABLED": "ignored_as_runtime_switch_after_PRD_036",
        "LEGACY_PIPELINE_ENABLED": "legacy_runtime_disabled_after_PRD_036",
    }
    assert payload["runtime_warnings"] == []

    thread_manager = payload["agents"]["thread_manager"]
    assert thread_manager["kind"] == "heuristic"
    assert thread_manager["llm_model_effective"] is False
    assert payload["response_planner"]["enabled"] is True
    assert payload["response_planner"]["version"] == "response_planner_v1"
    assert payload["response_planner"]["kind"] == "deterministic"
    assert payload["response_planner"]["live_acceptance_requires_api_trace"] is True
    assert payload["planner_drift_guard"]["enabled"] is True
    assert payload["planner_drift_guard"]["version"] == "planner_drift_guard_v1"
    assert payload["planner_drift_guard"]["mode"] == "observe_only"
    assert payload["planner_drift_guard"]["blocking_user_answers"] is False
    assert payload["planner_drift_guard"]["window_size"] == 100
    assert payload["planner_drift_guard"]["thresholds"]["warning_violation_rate"] == 0.10
    assert payload["planner_drift_guard"]["thresholds"]["critical_rate"] == 0.03
    assert isinstance(payload["planner_drift_guard"]["last_summary"], dict)
    assert isinstance(payload["planner_drift_guard"]["last_replay_status"], dict)
    assert payload["guided_live_testing"]["enabled"] is True
    assert payload["guided_live_testing"]["schema_version"] == "live_feedback_v1"
    assert payload["guided_live_testing"]["mode"] == "developer_local"
    assert payload["guided_live_testing"]["feedback_storage"] == "file_sanitized"
    assert payload["guided_live_testing"]["raw_dialogue_saved_by_default"] is False
    assert payload["guided_live_testing"]["scenario_set"] == "prd_047_7_guided_live_scenarios"
    assert isinstance(payload["guided_live_testing"]["scenario_count"], int)
    assert isinstance(payload["guided_live_testing"]["last_session_summary_available"], bool)
    assert payload["dialogue_profile"]["value"] in {"safe_guided", "mvp_free_dialogue"}
    assert "safe_guided" in payload["dialogue_profile"]["allowed_values"]
    assert "mvp_free_dialogue" in payload["dialogue_profile"]["allowed_values"]
    assert payload["dialogue_profile"]["scope"] == "developer_local"
    assert payload["dialogue_profile"]["developer_local_only"] is True
    assert payload["response_planner"]["advisory_mode"] in {True, False}
    assert payload["writer_freedom_contract"]["writer_max_tokens"] >= 600
    assert "dialogue_policy" in payload
    assert payload["dialogue_policy"]["profile"] in {"safe_guided", "mvp_free_dialogue"}
    assert payload["dialogue_policy"]["planner_authority"] in {"guided", "advisory"}
    assert payload["dialogue_policy"]["diagnostic_card_authority"] in {"guided", "advisory"}
    assert payload["dialogue_policy"]["writer_move_authority"] in {"guided", "advisory"}
    assert isinstance(payload["dialogue_policy"]["context_budget_chars"], int)
    assert payload["dialogue_policy"]["writer_runtime_max_tokens_effective"] >= 600
    assert isinstance(payload["dialogue_policy"]["human_like_answer_policy"], dict)
    assert isinstance(payload["dialogue_policy"]["constraint_resolution"], dict)
    assert payload["dialogue_policy"]["constraint_resolution"]["planner_authority"] in {"guided", "advisory"}

    assert payload["pipeline_mode"] not in {"legacy_adaptive", "hybrid"}


def test_runtime_effective_warns_when_legacy_flag_forced(admin_client, monkeypatch):
    monkeypatch.setenv("LEGACY_PIPELINE_ENABLED", "true")
    response = admin_client.get("/api/admin/runtime/effective", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    payload = response.json()
    assert payload["active_runtime"] == "multiagent"
    assert "LEGACY_PIPELINE_ENABLED is deprecated and ignored" in payload["runtime_warnings"]


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
