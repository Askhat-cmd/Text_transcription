from __future__ import annotations

import json
import sys
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.main import app


ADMIN_HEADERS = {"X-API-Key": "dev-key-001"}
QUERY_TEXT = "Что такое программа Несовершенное Я?"


def _build_ascii_stream_body(*, query: str, session_id: str) -> bytes:
    payload = {
        "query": str(query),
        "user_id": "owner-web-chat-user",
        "session_id": str(session_id),
        "include_path": False,
        "include_feedback_prompt": True,
        "debug": False,
    }
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode("ascii")


def _extract_done_payload(sse_text: str) -> dict[str, object]:
    for event in reversed([chunk for chunk in sse_text.split("\n\n") if chunk.strip()]):
        for line in event.splitlines():
            if not line.startswith("data:"):
                continue
            payload = json.loads(line.replace("data:", "", 1).strip())
            if payload.get("done") is True:
                return payload
    raise AssertionError("SSE done payload not found")


def test_admin_runtime_and_owner_like_trace_share_semantic_cards_truth(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("DEBUG_TRACE_ENABLED", "true")
    monkeypatch.setenv("SEMANTIC_CARDS_PILOT_ENABLED", "true")
    monkeypatch.setenv("WRITER_KB_PAYLOAD_ENABLED", "true")

    with TestClient(app, base_url="http://localhost") as client:
        runtime_response = client.get("/api/admin/runtime/effective", headers=ADMIN_HEADERS)
        assert runtime_response.status_code == 200
        runtime_payload = runtime_response.json()

        session_id = f"prd-047-27-hf2-owner-parity-{uuid4().hex}"
        stream_response = client.post(
            "/api/v1/questions/adaptive-stream",
            content=_build_ascii_stream_body(query=QUERY_TEXT, session_id=session_id),
            headers={**ADMIN_HEADERS, "Content-Type": "application/json; charset=utf-8"},
        )
        assert stream_response.status_code == 200
        done_payload = _extract_done_payload(stream_response.text)
        assert str(done_payload.get("answer", "") or "").strip()

        debug_response = client.get(
            f"/api/debug/session/{session_id}/multiagent-trace",
            headers=ADMIN_HEADERS,
        )

    assert debug_response.status_code == 200
    debug_payload = debug_response.json()
    runtime_trace = dict(runtime_payload.get("trace", {}).get("runtime_config_trace") or {})
    debug_runtime_trace = dict(debug_payload.get("runtime_config_trace") or {})
    semantic_trace = dict(debug_payload.get("semantic_cards_pilot") or {})
    writer_trace = dict(debug_payload.get("writer_kb_payload_trace") or {})

    assert runtime_trace["semantic_cards_pilot_enabled"] is True
    assert runtime_trace["semantic_cards_pilot_enabled_source"] == "env"
    assert runtime_trace["semantic_cards_pack_id"] == "semantic_cards_pilot_v1"
    assert int(runtime_trace["semantic_cards_loaded_count"]) >= 12

    assert debug_runtime_trace["semantic_cards_pilot_enabled"] is True
    assert debug_runtime_trace["semantic_cards_pilot_enabled_source"] == "env"
    assert debug_runtime_trace["semantic_cards_pack_id"] == runtime_trace["semantic_cards_pack_id"]
    assert debug_runtime_trace["semantic_cards_loaded_count"] == runtime_trace["semantic_cards_loaded_count"]
    assert debug_runtime_trace["backend_pid"] == runtime_trace["backend_pid"]
    assert debug_runtime_trace["backend_start_time"] == runtime_trace["backend_start_time"]

    assert semantic_trace["enabled"] is True
    assert semantic_trace["enabled_source"] == "env"
    assert semantic_trace["pack_id"] == "semantic_cards_pilot_v1"
    assert semantic_trace["loaded_card_count"] >= 12
    assert "program_imperfect_self_v1" in list(semantic_trace.get("selected_card_ids", []) or [])

    chunk_summaries = list(writer_trace.get("chunk_summaries", []) or [])
    assert any(item.get("semantic_card_id") == "program_imperfect_self_v1" for item in chunk_summaries)


def test_pilot_manual_startup_protocol_includes_semantic_cards_env() -> None:
    startup_text = (REPO_ROOT / "запуск проека.txt").read_text(encoding="utf-8")
    pilot_script_text = (
        REPO_ROOT / "bot_psychologist" / "tools" / "start_pilot_web_chat_backend.ps1"
    ).read_text(encoding="utf-8")

    assert '$env:SEMANTIC_CARDS_PILOT_ENABLED="true"' in startup_text
    assert '$env:SEMANTIC_CARDS_PILOT_ENABLED = "true"' in pilot_script_text
