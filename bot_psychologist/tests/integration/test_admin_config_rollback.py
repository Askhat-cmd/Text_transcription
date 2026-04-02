from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

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
        yield client, override_path


def test_admin_import_invalid_payload_rolls_back(admin_client):
    client, override_path = admin_client

    seed = client.post(
        "/api/v1/admin/config",
        headers=ADMIN_HEADERS,
        json={"routing": {"FREE_CONVERSATION_MODE": True}},
    )
    assert seed.status_code == 200

    before_payload = client.get("/api/admin/export", headers=ADMIN_HEADERS).json()

    bad_import = client.post(
        "/api/admin/import",
        headers=ADMIN_HEADERS,
        json={
            "config": {"TOP_K_BLOCKS": 0},
            "prompts": {},
            "meta": {},
            "history": [],
        },
    )
    assert bad_import.status_code == 422

    after_payload = client.get("/api/admin/export", headers=ADMIN_HEADERS).json()
    assert after_payload == before_payload

    disk_payload = json.loads(Path(override_path).read_text(encoding="utf-8"))
    assert disk_payload == before_payload
