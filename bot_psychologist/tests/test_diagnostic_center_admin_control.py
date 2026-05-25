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

    with TestClient(app, base_url="http://localhost") as client:
        yield client


def test_effective_endpoint_returns_schema(admin_client: TestClient) -> None:
    response = admin_client.get("/api/v1/admin/diagnostic-center/effective", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_version"] == "diagnostic_center_control_v1"
    assert "current_mode" in payload
    assert "boundary_flags" in payload
    assert "last_evidence" in payload


def test_default_mode_is_safe(admin_client: TestClient) -> None:
    response = admin_client.get("/api/v1/admin/diagnostic-center/effective", headers=ADMIN_HEADERS)
    payload = response.json()
    assert payload["current_mode"] == "creator_only"
    assert payload["force_disabled"] is False


def test_mode_update_works(admin_client: TestClient) -> None:
    response = admin_client.post(
        "/api/v1/admin/diagnostic-center/control",
        headers=ADMIN_HEADERS,
        json={"mode": "allowlist", "force_disabled": False, "allowlist_user_ids": ["creator"]},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["current_mode"] == "allowlist"
    assert payload["developer_identity"]["allowlist_user_ids"] == ["creator"]


def test_invalid_mode_rejected(admin_client: TestClient) -> None:
    response = admin_client.post(
        "/api/v1/admin/diagnostic-center/control",
        headers=ADMIN_HEADERS,
        json={"mode": "unknown_mode"},
    )
    assert response.status_code == 422


def test_force_disabled_overrides_active_state(admin_client: TestClient) -> None:
    response = admin_client.post(
        "/api/v1/admin/diagnostic-center/control",
        headers=ADMIN_HEADERS,
        json={"mode": "creator_only", "force_disabled": True},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["force_disabled"] is True
    assert payload["effective_active"] is False


def test_developer_all_users_keeps_production_flags_false(admin_client: TestClient) -> None:
    response = admin_client.post(
        "/api/v1/admin/diagnostic-center/control",
        headers=ADMIN_HEADERS,
        json={"mode": "developer_local_all_users", "force_disabled": False},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["current_mode"] == "developer_local_all_users"
    assert payload["boundary_flags"]["production_ready"] is False
    assert payload["boundary_flags"]["broad_rollout_allowed"] is False
    assert payload["boundary_flags"]["normal_user_activation_allowed"] is False


def test_reset_returns_safe_default(admin_client: TestClient) -> None:
    admin_client.post(
        "/api/v1/admin/diagnostic-center/control",
        headers=ADMIN_HEADERS,
        json={"mode": "developer_local_all_users", "force_disabled": False},
    )
    response = admin_client.post("/api/v1/admin/diagnostic-center/reset", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    payload = response.json()
    assert payload["current_mode"] == "creator_only"
    assert payload["force_disabled"] is False


def test_allowlist_is_sanitized(admin_client: TestClient) -> None:
    response = admin_client.post(
        "/api/v1/admin/diagnostic-center/control",
        headers=ADMIN_HEADERS,
        json={
            "mode": "allowlist",
            "allowlist_user_ids": [" creator ", "", "creator", "pilot_001"],
            "force_disabled": False,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["developer_identity"]["allowlist_user_ids"] == ["creator", "pilot_001"]


def test_runtime_effective_contains_diagnostic_center_snapshot(admin_client: TestClient) -> None:
    response = admin_client.get("/api/v1/admin/runtime/effective", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    payload = response.json()
    snapshot = payload["diagnostic_center_control"]
    serialized = str(snapshot)
    assert "OPENAI_API_KEY" not in serialized
    assert "sk-" not in serialized
