from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from api.main import app
from bot_agent.config import config
from bot_agent.runtime_config import RuntimeConfig
from bot_agent.prompt_registry_v2 import PROMPT_STACK_ORDER, PROMPT_STACK_VERSION


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


def test_prompt_stack_v2_list_matches_runtime_contract(admin_client):
    response = admin_client.get("/api/v1/admin/prompts/stack-v2", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    payload = response.json()
    assert [item["name"] for item in payload] == list(PROMPT_STACK_ORDER)
    assert all(item["stack_version"] == PROMPT_STACK_VERSION for item in payload)
    assert all("version" in item for item in payload)


def test_prompt_stack_v2_detail_and_editability(admin_client):
    detail = admin_client.get("/api/v1/admin/prompts/stack-v2/CORE_IDENTITY", headers=ADMIN_HEADERS)
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["editable"] is True
    assert payload["legacy_prompt_name"] == "prompt_system_base"
    assert payload["default_text"]

    readonly_detail = admin_client.get("/api/v1/admin/prompts/stack-v2/AA_SAFETY", headers=ADMIN_HEADERS).json()
    assert readonly_detail["editable"] is False
