from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app


ADMIN_HEADERS = {"X-API-Key": "dev-key-001"}


def test_runtime_effective_exposes_semantic_cards_runtime_status(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("SEMANTIC_CARDS_PILOT_ENABLED", "true")
    monkeypatch.setenv("WRITER_KB_PAYLOAD_ENABLED", "true")

    with TestClient(app, base_url="http://localhost") as client:
        response = client.get("/api/admin/runtime/effective", headers=ADMIN_HEADERS)

    assert response.status_code == 200
    payload = response.json()
    semantic_cards = payload["semantic_cards_pilot"]

    assert semantic_cards["enabled"] is True
    assert semantic_cards["pack_id"] == "semantic_cards_pilot_v1"
    assert semantic_cards["loaded_card_count"] >= 12
    assert semantic_cards["adapter_enabled"] is True
    assert semantic_cards["writer_payload_enabled"] is True
    assert semantic_cards["selection_surface"] == "per_turn_trace_only"
    assert semantic_cards["selected_cards_visible_in_turn_trace"] is True
    assert semantic_cards["authority"] == "advisory_only"
    assert semantic_cards["writer_can_ignore"] is True
    assert semantic_cards["applied_as_authority"] is False
    assert payload["trace"]["runtime_config_trace"]["semantic_cards_pilot_enabled"] is True
    assert payload["trace"]["runtime_config_trace"]["semantic_cards_pilot_enabled_source"] == "env"


def test_runtime_effective_exposes_disabled_reason_when_pilot_is_off(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("SEMANTIC_CARDS_PILOT_ENABLED", "false")

    with TestClient(app, base_url="http://localhost") as client:
        response = client.get("/api/admin/runtime/effective", headers=ADMIN_HEADERS)

    assert response.status_code == 200
    payload = response.json()
    semantic_cards = payload["semantic_cards_pilot"]

    assert semantic_cards["enabled"] is False
    assert semantic_cards["status"] == "disabled"
    assert semantic_cards["reason"] == "disabled_by_config"
    assert semantic_cards["pack_id"] == "semantic_cards_pilot_v1"
    assert semantic_cards["loaded_card_count"] >= 12
