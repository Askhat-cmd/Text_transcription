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
        "prompt-flow-session",
        {
            "turn_number": 3,
            "prompt_stack_v2": {
                "enabled": True,
                "version": "2.0",
                "order": ["AA_SAFETY", "CORE_IDENTITY", "STYLE_CONTRACT"],
                "sections": {
                    "AA_SAFETY": 110,
                    "CORE_IDENTITY": 230,
                    "STYLE_CONTRACT": 90,
                },
            },
        },
    )

    with TestClient(app, base_url="http://localhost") as client:
        yield client


def test_prompt_operational_surface_flow(admin_client):
    list_response = admin_client.get("/api/admin/prompts/stack-v2", headers=ADMIN_HEADERS)
    assert list_response.status_code == 200
    stack_sections = list_response.json()
    assert isinstance(stack_sections, list)
    assert stack_sections, "stack sections should not be empty"

    usage_response = admin_client.get("/api/admin/prompts/stack-v2/usage", headers=ADMIN_HEADERS)
    assert usage_response.status_code in {404, 410}
    if usage_response.status_code == 410:
        assert "deprecated" in str(usage_response.json().get("detail", "")).lower()

    core_detail = admin_client.get("/api/admin/prompts/stack-v2/CORE_IDENTITY", headers=ADMIN_HEADERS)
    assert core_detail.status_code == 200
    core_payload = core_detail.json()
    assert core_payload["editable"] is True

    update_response = admin_client.put(
        "/api/admin/prompts/stack-v2/CORE_IDENTITY",
        headers=ADMIN_HEADERS,
        json={"text": "This is a temporary override for CORE_IDENTITY section in phase 10.4.1 tests."},
    )
    assert update_response.status_code == 200
    updated_payload = update_response.json()
    assert updated_payload["is_overridden"] is True

    reset_response = admin_client.post("/api/admin/prompts/stack-v2/CORE_IDENTITY/reset", headers=ADMIN_HEADERS)
    assert reset_response.status_code == 200
    reset_payload = reset_response.json()
    assert reset_payload["is_overridden"] is False
