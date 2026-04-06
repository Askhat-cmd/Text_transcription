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


def test_admin_trace_viewer_last_turn_flow(admin_client):
    last_trace = admin_client.get("/api/admin/trace/last", headers=ADMIN_HEADERS)
    assert last_trace.status_code in {404, 410}

    recent = admin_client.get("/api/admin/trace/recent?limit=5", headers=ADMIN_HEADERS)
    assert recent.status_code in {404, 410}
