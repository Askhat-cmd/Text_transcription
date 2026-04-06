from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from api.main import app
from api.session_store import get_session_store
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

    store = get_session_store()
    monkeypatch.setattr(store, "_sessions", {}, raising=False)
    monkeypatch.setattr(store, "_blobs", {}, raising=False)
    store.append_trace(
        "diag-session",
        {
            "turn_number": 4,
            "diagnostics_v1": {
                "interaction_mode": "curious",
                "nervous_system_state": "window",
                "request_function": "understand",
                "core_theme": "self-inquiry",
                "informational_mode_hint": False,
                "mixed_query": True,
                "confidence": 0.74,
            },
        },
    )

    with TestClient(app, base_url="http://localhost") as client:
        yield client


def test_admin_diagnostics_effective_payload_shape(admin_client):
    response = admin_client.get("/api/v1/admin/diagnostics/effective", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    payload = response.json()

    assert payload["schema_version"] == "10.5.1"
    assert payload["contract"] == "diagnostics-v1"
    assert isinstance(payload["policies"], dict)
    assert "informational_narrowing_enabled" in payload["policies"]
    assert "mixed_query_handling_enabled" in payload["policies"]
    assert "user_correction_protocol_enabled" in payload["policies"]
    assert "curiosity_decoupling_enabled" in payload["policies"]

    assert isinstance(payload["active_contract"], dict)
    assert payload["active_contract"]["contract_version"] == "diagnostics-v1"
    assert payload["active_contract"]["interaction_mode_policy"] == "system-level"
    assert payload["active_contract"]["nervous_system_taxonomy"] == "window|activation|shutdown"
    assert payload["active_contract"]["request_function_taxonomy"] == "understand|practice|regulate|contact"
    assert payload["last_snapshot"] == {}
    assert payload["trace_available"] is False
