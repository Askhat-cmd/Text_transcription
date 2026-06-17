from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.main import app
from bot_agent.feature_flags import feature_flags


ADMIN_HEADERS = {"X-API-Key": "dev-key-001"}


def test_local_runtime_defaults_enable_writer_kb_payload(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.delenv("WRITER_KB_PAYLOAD_ENABLED", raising=False)

    resolution = feature_flags.resolve_bool("WRITER_KB_PAYLOAD_ENABLED")
    assert resolution["effective_value"] is True
    assert resolution["source"] == "default_local"

    with TestClient(app, base_url="http://localhost") as client:
        response = client.get("/api/admin/runtime/effective", headers=ADMIN_HEADERS)

    assert response.status_code == 200
    payload = response.json()
    writer_payload = payload["writer_kb_payload"]
    assert writer_payload["enabled"] is True
    assert writer_payload["enabled_source"] == "default_local"
    assert payload["trace"]["runtime_config_trace"]["writer_kb_payload_enabled"] is True
    assert payload["trace"]["runtime_config_trace"]["writer_kb_payload_enabled_source"] == "default_local"


def test_production_runtime_does_not_silently_enable_writer_kb_payload(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("WRITER_KB_PAYLOAD_ENABLED", raising=False)

    with TestClient(app, base_url="http://localhost") as client:
        response = client.get("/api/admin/runtime/effective", headers=ADMIN_HEADERS)

    assert response.status_code == 200
    payload = response.json()
    writer_payload = payload["writer_kb_payload"]
    assert writer_payload["enabled"] is False
    assert writer_payload["enabled_source"] == "default_safe_off"


def test_explicit_disable_is_visible_in_effective_runtime(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("WRITER_KB_PAYLOAD_ENABLED", "false")

    with TestClient(app, base_url="http://localhost") as client:
        response = client.get("/api/admin/runtime/effective", headers=ADMIN_HEADERS)

    assert response.status_code == 200
    payload = response.json()
    writer_payload = payload["writer_kb_payload"]
    assert writer_payload["enabled"] is False
    assert writer_payload["enabled_source"] == "env"
    assert payload["trace"]["runtime_config_trace"]["writer_kb_payload_enabled_source"] == "env"
