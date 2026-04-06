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


def test_admin_prompt_edit_and_runtime_status_flow(admin_client) -> None:
    runtime = admin_client.get("/api/admin/runtime/effective", headers=ADMIN_HEADERS)
    assert runtime.status_code == 200

    prompts = admin_client.get("/api/admin/prompts/stack-v2", headers=ADMIN_HEADERS)
    assert prompts.status_code == 200
    editable = next(item for item in prompts.json() if item.get("editable"))
    section = editable["name"]

    detail = admin_client.get(f"/api/admin/prompts/stack-v2/{section}", headers=ADMIN_HEADERS)
    assert detail.status_code == 200
    original = detail.json()["text"]
    updated_text = f"{original}\n\n[admin-test]"

    saved = admin_client.put(
        f"/api/admin/prompts/stack-v2/{section}",
        headers=ADMIN_HEADERS,
        json={"text": updated_text},
    )
    assert saved.status_code == 200
    assert saved.json()["text"].endswith("[admin-test]")

    reset = admin_client.post(f"/api/admin/prompts/stack-v2/{section}/reset", headers=ADMIN_HEADERS)
    assert reset.status_code == 200
