from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from api.main import app
from api.session_store import get_session_store
from bot_agent.config import config
from bot_agent.runtime_config import RuntimeConfig


ADMIN_HEADERS = {"X-API-Key": "dev-key-001"}


@pytest.fixture()
def admin_client_without_traces(tmp_path, monkeypatch):
    override_path = tmp_path / "admin_overrides.json"
    monkeypatch.setattr(RuntimeConfig, "OVERRIDES_PATH", override_path, raising=False)
    monkeypatch.setattr(RuntimeConfig, "_cache_mtime", 0.0, raising=False)
    monkeypatch.setattr(RuntimeConfig, "_cache", {}, raising=False)
    monkeypatch.setattr(config, "OVERRIDES_PATH", override_path, raising=False)
    monkeypatch.setattr(config, "WARMUP_ON_START", False, raising=False)

    store = get_session_store()
    monkeypatch.setattr(store, "_sessions", {}, raising=False)
    monkeypatch.setattr(store, "_blobs", {}, raising=False)

    with TestClient(app, base_url="http://localhost") as client:
        yield client


def test_admin_payloads_no_message_level_trace_dependency(admin_client_without_traces) -> None:
    runtime = admin_client_without_traces.get("/api/v1/admin/runtime/effective", headers=ADMIN_HEADERS)
    diagnostics = admin_client_without_traces.get("/api/v1/admin/diagnostics/effective", headers=ADMIN_HEADERS)

    assert runtime.status_code == 200
    assert diagnostics.status_code == 200
    assert runtime.json()["trace"]["available"] is False
    assert diagnostics.json()["last_snapshot"] == {}
    assert diagnostics.json()["trace_available"] is False
