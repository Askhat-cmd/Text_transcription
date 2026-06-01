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


def test_runtime_effective_has_writer_first_policy_block(admin_client) -> None:
    response = admin_client.get("/api/v1/admin/runtime/effective", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    payload = response.json()
    policy = payload.get("dialogue_policy", {})
    assert "final_answer_directive_enabled" in policy
    assert "final_answer_directive_version" in policy
    assert "legacy_prompt_blocks_mode" in policy
    assert "writer_first_prompt_assembly_enabled" in policy
    assert "diagnostic_center_role" in policy
    assert "planner_role" in policy

