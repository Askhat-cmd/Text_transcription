from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from api.main import app
from bot_agent.config import config
from bot_agent.runtime_config import RuntimeConfig


ADMIN_HEADERS = {"X-API-Key": "dev-key-001"}
REPO_ROOT = Path(__file__).resolve().parents[3]
ADMIN_PANEL_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/components/admin/AdminPanel.tsx"


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


def test_admin_management_flow_without_trace_surface(admin_client) -> None:
    text = ADMIN_PANEL_PATH.read_text(encoding="utf-8", errors="ignore")
    assert "key: 'trace'" not in text

    runtime = admin_client.get("/api/admin/runtime/effective", headers=ADMIN_HEADERS)
    diagnostics = admin_client.get("/api/admin/diagnostics/effective", headers=ADMIN_HEADERS)
    assert runtime.status_code == 200
    assert diagnostics.status_code == 200
