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


def test_admin_management_tabs_still_load_after_backend_cleanup(admin_client) -> None:
    endpoints = [
        "/api/admin/config",
        "/api/admin/prompts/stack-v2",
        "/api/admin/status",
        "/api/admin/runtime/effective",
        "/api/admin/diagnostics/effective",
    ]

    for endpoint in endpoints:
        response = admin_client.get(endpoint, headers=ADMIN_HEADERS)
        assert response.status_code == 200, f"{endpoint} should stay operational"

