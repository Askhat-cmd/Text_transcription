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


def test_prompt_management_and_runtime_status_still_work(admin_client) -> None:
    prompt_name = "CORE_IDENTITY"
    new_text = "Neo runtime identity override for regression validation in admin management surface."

    set_response = admin_client.put(
        f"/api/admin/prompts/stack-v2/{prompt_name}",
        headers=ADMIN_HEADERS,
        json={"text": new_text},
    )
    assert set_response.status_code == 200
    assert set_response.json()["text"] == new_text

    status_response = admin_client.get("/api/admin/status", headers=ADMIN_HEADERS)
    runtime_response = admin_client.get("/api/admin/runtime/effective", headers=ADMIN_HEADERS)

    assert status_response.status_code == 200
    assert runtime_response.status_code == 200
    runtime_payload = runtime_response.json()
    assert runtime_payload["trace"]["developer_trace_supported"] is True
    assert runtime_payload["trace"]["developer_trace_enabled"] is True

    reset_response = admin_client.post(
        f"/api/admin/prompts/stack-v2/{prompt_name}/reset",
        headers=ADMIN_HEADERS,
    )
    assert reset_response.status_code == 200

