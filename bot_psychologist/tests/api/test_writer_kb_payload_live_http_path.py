from __future__ import annotations

from pathlib import Path
import sys
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api import dependencies as deps
from api.main import app
from bot_agent.config import config
from tools.run_prd_047_22_hf1_live_api_smoke import QUERY_TEXT, build_ascii_json_body


DEV_HEADERS = {
    "X-API-Key": "dev-key-001",
    "X-Session-Id": "test-writer-kb-live-http",
    "X-Device-Fingerprint": "test-writer-kb-live-http-fp",
    "Content-Type": "application/json; charset=utf-8",
}


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch):
    temp_dir = PROJECT_ROOT / ".tmp_test_artifacts" / f"writer_kb_payload_live_http_{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(config, "WARMUP_ON_START", False, raising=False)
    monkeypatch.setattr(
        config,
        "BOT_DB_PATH",
        temp_dir / "writer_kb_payload_live_http.db",
        raising=False,
    )
    monkeypatch.setattr(deps, "_identity_repository", None, raising=False)
    monkeypatch.setattr(deps, "_identity_service", None, raising=False)
    monkeypatch.setattr(deps, "_conversation_repository", None, raising=False)
    monkeypatch.setattr(deps, "_conversation_service", None, raising=False)
    monkeypatch.setattr(deps, "_registration_repository", None, raising=False)
    monkeypatch.setattr(deps, "_registration_service", None, raising=False)
    monkeypatch.setattr(deps, "_database_bootstrap", None, raising=False)
    with TestClient(app, base_url="http://localhost") as test_client:
        yield test_client


def test_build_ascii_json_body_roundtrips_russian_query() -> None:
    body = build_ascii_json_body(QUERY_TEXT, "sid-1")
    decoded = body.decode("ascii")
    assert "\\u041d\\u0435\\u0439\\u0440\\u043e\\u0441\\u0442\\u0430\\u043b\\u043a\\u0438\\u043d\\u0433" in decoded
    assert '"session_id":"sid-1"' in decoded


def test_live_like_http_path_produces_writer_kb_payload_trace(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.delenv("WRITER_KB_PAYLOAD_ENABLED", raising=False)

    session_id = "test-writer-kb-live-http-path"
    response = client.post(
        "/api/v1/questions/adaptive",
        content=build_ascii_json_body(QUERY_TEXT, session_id),
        headers={
            **DEV_HEADERS,
            "X-Session-Id": session_id,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    answer = str(payload.get("answer", "") or "")
    assert "WRITER KB PAYLOAD" not in answer
    assert "writer_kb_payload" not in answer
    assert "**РќРµРѕРЎС‚Р°Р»РєРёРЅРі** вЂ” СЌС‚Рѕ РІ" not in answer

    debug_response = client.get(
        f"/api/debug/session/{session_id}/multiagent-trace",
        headers={"X-API-Key": "dev-key-001"},
    )
    assert debug_response.status_code == 200
    debug_payload = debug_response.json()
    runtime_trace = dict(debug_payload.get("runtime_config_trace") or {})
    trace = dict(debug_payload.get("writer_kb_payload_trace") or {})
    assert runtime_trace["writer_kb_payload_enabled"] is True
    assert runtime_trace["writer_kb_payload_enabled_source"] == "default_local"
    assert trace["enabled"] is True
    assert trace["primary_path"] == "writer_kb_payload_v1"
    assert trace["status"] == "structured_payload_used"
    assert int(trace["payload_chunk_count"]) >= 1
    assert int(trace["mid_sentence_cut_count"]) == 0
    assert trace["fallback_is_primary"] is False


def test_live_like_http_path_exposes_semantic_cards_pilot_when_selected(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("SEMANTIC_CARDS_PILOT_ENABLED", "true")
    monkeypatch.delenv("WRITER_KB_PAYLOAD_ENABLED", raising=False)

    session_id = "test-semantic-cards-live-http-path"
    response = client.post(
        "/api/v1/questions/adaptive",
        content=build_ascii_json_body('Что такое программа "Несовершенное Я"?', session_id),
        headers={
            **DEV_HEADERS,
            "X-Session-Id": session_id,
        },
    )
    assert response.status_code == 200

    debug_response = client.get(
        f"/api/debug/session/{session_id}/multiagent-trace",
        headers={"X-API-Key": "dev-key-001"},
    )
    assert debug_response.status_code == 200
    debug_payload = debug_response.json()
    runtime_trace = dict(debug_payload.get("runtime_config_trace") or {})
    semantic_trace = dict(debug_payload.get("semantic_cards_pilot") or {})
    assert runtime_trace["semantic_cards_pilot_enabled"] is True
    assert semantic_trace["schema_version"] == "semantic_cards_pilot_trace_v1"
    assert int(semantic_trace["selected_card_count"]) >= 1
    assert "program_imperfect_self_v1" in list(semantic_trace.get("selected_card_ids") or [])
    assert semantic_trace["writer_can_ignore"] is True
    assert semantic_trace["applied_as_authority"] is False
