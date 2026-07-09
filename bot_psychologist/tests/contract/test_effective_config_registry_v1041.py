from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from api.main import app
from bot_agent.config import config
from bot_agent.effective_config_registry import (
    EXPECTED_NON_ENV_EDITABLE_CONFIG_KEYS,
    EXPECTED_ENV_EDITABLE_COUNT,
    FLAG_REGISTRY,
    SECRET_FLAGS,
    TOTAL_FLAG_COUNT,
    build_effective_config_payload,
    get_admin_hot_editable_env_flags,
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


def test_effective_config_registry_counts_and_alignment() -> None:
    payload = build_effective_config_payload()
    editable_env_intersection = set(RuntimeConfig.EDITABLE_CONFIG).intersection(FLAG_REGISTRY)

    assert len(FLAG_REGISTRY) == TOTAL_FLAG_COUNT
    assert payload["flag_count"] == TOTAL_FLAG_COUNT
    assert payload["status_counts"] == {
        "active_tunable": 51,
        "frozen_constant": 41,
        "retirement_candidate_deferred": 1,
        "secret": 10,
    }
    assert payload["admin_hot_editable_count"] == EXPECTED_ENV_EDITABLE_COUNT
    assert payload["editable_config_env_intersection_count"] == EXPECTED_ENV_EDITABLE_COUNT
    assert set(payload["entries"]) == set(FLAG_REGISTRY)
    assert get_admin_hot_editable_env_flags() == editable_env_intersection
    assert payload["editable_config_non_env_keys"] == EXPECTED_NON_ENV_EDITABLE_CONFIG_KEYS


def test_effective_config_secret_entries_export_is_set_only(monkeypatch) -> None:
    for name in SECRET_FLAGS:
        monkeypatch.setenv(name, f"sentinel::{name.lower()}")

    payload = build_effective_config_payload()
    for name in SECRET_FLAGS:
        entry = payload["entries"][name]
        assert entry["status"] == "secret"
        assert entry["current_value"] == {"is_set": True}


def test_admin_runtime_effective_exposes_effective_config_registry(admin_client) -> None:
    response = admin_client.get("/api/admin/runtime/effective", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    payload = response.json()

    effective_config = payload["effective_config"]
    assert effective_config["schema_version"] == "effective_config_registry_v1"
    assert effective_config["flag_count"] == TOTAL_FLAG_COUNT
    assert effective_config["admin_hot_editable_count"] == EXPECTED_ENV_EDITABLE_COUNT
    assert effective_config["entries"]["LEGACY_PIPELINE_ENABLED"]["status"] == "retirement_candidate_deferred"
    assert effective_config["entries"]["MULTIAGENT_ENABLED"]["source"] == "constant"


def test_admin_debug_endpoints_do_not_leak_secret_values(admin_client, monkeypatch) -> None:
    sentinels: dict[str, str] = {}
    for name in SECRET_FLAGS:
        sentinel = f"secret-sentinel::{name.lower()}"
        sentinels[name] = sentinel
        monkeypatch.setenv(name, sentinel)

    payloads = [
        admin_client.get("/api/admin/runtime/effective", headers=ADMIN_HEADERS).json(),
        admin_client.get("/api/admin/orchestrator/config", headers=ADMIN_HEADERS).json(),
        admin_client.get("/api/admin/overview", headers=ADMIN_HEADERS).json(),
        admin_client.get("/api/admin/config", headers=ADMIN_HEADERS).json(),
    ]
    dumped = json.dumps(payloads, ensure_ascii=False)

    for sentinel in sentinels.values():
        assert sentinel not in dumped

    effective_entries = payloads[0]["effective_config"]["entries"]
    for name in SECRET_FLAGS:
        assert effective_entries[name]["current_value"] == {"is_set": True}

