from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from api.main import app
from api.session_store import get_session_store
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


def _raise_if_called(*_args, **_kwargs):
    raise AssertionError("get_last_trace should not be called by /runtime/effective")


def test_admin_runtime_payload_not_derived_from_last_trace(admin_client, monkeypatch) -> None:
    store = get_session_store()
    monkeypatch.setattr(store, "get_last_trace", _raise_if_called, raising=True)

    response = admin_client.get("/api/admin/runtime/effective", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    payload = response.json()

    trace = payload["trace"]
    assert trace["available"] is True
    assert trace["developer_trace_supported"] is True
    assert trace["developer_trace_enabled"] is True
    assert trace["developer_trace_mode_available"] is True


def test_admin_runtime_payload_with_session_id_still_not_trace_derived(admin_client, monkeypatch) -> None:
    store = get_session_store()
    monkeypatch.setattr(store, "get_last_trace", _raise_if_called, raising=True)

    response = admin_client.get(
        "/api/admin/runtime/effective?session_id=any-session",
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 200
    assert response.json()["trace"]["developer_trace_supported"] is True

