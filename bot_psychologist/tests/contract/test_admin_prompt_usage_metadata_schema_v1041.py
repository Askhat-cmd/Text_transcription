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
        "prompt-session",
        {
            "turn_number": 11,
            "prompt_stack_v2": {
                "enabled": True,
                "version": "2.0",
                "order": ["AA_SAFETY", "A_STYLE_POLICY", "CORE_IDENTITY"],
                "sections": {"AA_SAFETY": 120, "CORE_IDENTITY": 240},
            },
        },
    )

    with TestClient(app, base_url="http://localhost") as client:
        yield client


def test_admin_prompt_usage_metadata_schema(admin_client):
    response = admin_client.get("/api/v1/admin/prompts/stack-v2/usage", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    payload = response.json()

    assert payload["schema_version"] == "10.4.1"
    assert payload["prompt_stack_version"] == "2.0"
    assert payload["last_turn_available"] is True
    assert payload["last_turn"]["turn_number"] == 11
    assert "used_sections" in payload["last_turn"]
    assert isinstance(payload["sections"], list)
    assert payload["sections"], "sections must not be empty"

    sample = payload["sections"][0]
    assert "name" in sample
    assert "editable" in sample
    assert "source" in sample
    assert "derived_from" in sample
    assert "read_only_reason" in sample
    assert "usage_markers" in sample

