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


def test_admin_export_import_metadata_uses_105_family(admin_client) -> None:
    exported = admin_client.get("/api/admin/export", headers=ADMIN_HEADERS)
    assert exported.status_code == 200
    exported_payload = exported.json()
    assert exported_payload["meta"]["schema_family"] == "admin_overrides"
    assert exported_payload["meta"]["schema_version"] == "10.5"

    imported = admin_client.post("/api/admin/import", headers=ADMIN_HEADERS, json=exported_payload)
    assert imported.status_code == 200
    imported_payload = imported.json()
    assert imported_payload["schema_version"] == "10.5"
    assert imported_payload["imported_schema_version"] == "10.5"

