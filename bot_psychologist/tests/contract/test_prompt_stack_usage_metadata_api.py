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

    with TestClient(app, base_url="http://localhost") as client:
        yield client


def test_prompt_stack_usage_metadata_api_without_trace(admin_client):
    response = admin_client.get("/api/admin/prompts/stack-v2/usage", headers=ADMIN_HEADERS)
    assert response.status_code == 200

    payload = response.json()
    assert payload["schema_version"] == "10.4.1"
    assert payload["last_turn_available"] is False
    assert isinstance(payload["sections"], list)
    assert payload["sections"], "sections must not be empty"

    first = payload["sections"][0]
    assert "derived_from" in first
    assert "read_only_reason" in first
    assert "usage_markers" in first


def test_prompt_stack_usage_metadata_api_marks_used_sections(admin_client):
    store = get_session_store()
    store.append_trace(
        "usage-session",
        {
            "turn_number": 7,
            "prompt_stack_v2": {
                "enabled": True,
                "version": "2.0",
                "order": ["AA_SAFETY", "CORE_IDENTITY"],
                "sections": {
                    "AA_SAFETY": 120,
                    "CORE_IDENTITY": 210,
                },
            },
        },
    )

    response = admin_client.get("/api/admin/prompts/stack-v2/usage", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    payload = response.json()

    assert payload["last_turn_available"] is True
    assert payload["last_turn"]["turn_number"] == 7
    used_sections = set(payload["last_turn"]["used_sections"])
    assert "CORE_IDENTITY" in used_sections

    sections = {item["name"]: item for item in payload["sections"]}
    assert sections["CORE_IDENTITY"]["editable"] is True
    assert sections["CORE_IDENTITY"]["usage_markers"]["used_in_last_turn"] is True
