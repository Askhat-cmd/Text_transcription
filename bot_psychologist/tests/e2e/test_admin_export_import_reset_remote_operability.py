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


def test_admin_export_import_reset_remote_operability(admin_client) -> None:
    exported = admin_client.get("/api/admin/export", headers=ADMIN_HEADERS)
    assert exported.status_code == 200
    payload = exported.json()
    assert "meta" in payload

    imported = admin_client.post("/api/admin/import", headers=ADMIN_HEADERS, json=payload)
    assert imported.status_code == 200

    reset = admin_client.post("/api/admin/reset-all", headers=ADMIN_HEADERS)
    assert reset.status_code == 200
