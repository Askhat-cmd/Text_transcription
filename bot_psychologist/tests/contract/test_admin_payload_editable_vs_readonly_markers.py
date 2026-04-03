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


def test_v104_schema_contains_editable_markers_for_all_editable_params(admin_client):
    payload = admin_client.get("/api/v1/admin/config/schema-v104", headers=ADMIN_HEADERS).json()
    groups = payload["editable"]["groups"]

    for group in groups.values():
        for param in group["params"].values():
            assert param["editable"] is True
            assert param["read_only"] is False
            assert "deprecated" in param
            assert "compatibility_only" in param


def test_v104_schema_contains_read_only_markers_for_runtime_and_flags(admin_client):
    payload = admin_client.get("/api/v1/admin/config/schema-v104", headers=ADMIN_HEADERS).json()
    read_only = payload["read_only"]

    for section_name in ("runtime_status", "feature_flags"):
        assert section_name in read_only
        section = read_only[section_name]
        assert section, f"{section_name} must not be empty"
        for field in section.values():
            assert field["editable"] is False
            assert field["read_only"] is True
            assert field["deprecated"] is False
            assert field["compatibility_only"] is False
