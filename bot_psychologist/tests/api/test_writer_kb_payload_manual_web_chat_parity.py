from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.main import app
from tools.run_prd_047_22_hf1_live_api_smoke import QUERY_TEXT


DEV_HEADERS = {
    "X-API-Key": "dev-key-001",
    "Content-Type": "application/json; charset=utf-8",
}


def _build_ascii_stream_body(*, query: str, session_id: str) -> bytes:
    payload = {
        "query": str(query),
        "user_id": "web-chat-parity-user",
        "session_id": str(session_id),
        "include_path": False,
        "include_feedback_prompt": True,
        "debug": False,
    }
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode("ascii")


def _extract_done_payload(sse_text: str) -> dict[str, object]:
    events = [chunk for chunk in sse_text.split("\n\n") if chunk.strip()]
    for event in reversed(events):
        for line in event.splitlines():
            if not line.startswith("data:"):
                continue
            payload = json.loads(line.replace("data:", "", 1).strip())
            if payload.get("done") is True:
                return payload
    raise AssertionError("SSE done payload not found")


def test_manual_web_chat_stream_path_uses_writer_kb_payload_v1_by_default_local(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.delenv("WRITER_KB_PAYLOAD_ENABLED", raising=False)

    with TestClient(app, base_url="http://localhost") as client:
        session_id = "writer-kb-manual-web-chat"
        response = client.post(
            "/api/v1/questions/adaptive-stream",
            content=_build_ascii_stream_body(query=QUERY_TEXT, session_id=session_id),
            headers=DEV_HEADERS,
        )
        assert response.status_code == 200
        done_payload = _extract_done_payload(response.text)
        answer = str(done_payload.get("answer", "") or "")
        assert "WRITER KB PAYLOAD" not in answer
        assert "writer_kb_payload" not in answer

        debug_response = client.get(
            f"/api/debug/session/{session_id}/multiagent-trace",
            headers={"X-API-Key": "dev-key-001"},
        )

    assert debug_response.status_code == 200
    debug_payload = debug_response.json()
    runtime_trace = dict(debug_payload.get("runtime_config_trace") or {})
    writer_trace = dict(debug_payload.get("writer_kb_payload_trace") or {})

    assert runtime_trace["app_env"] == "local"
    assert runtime_trace["writer_kb_payload_enabled"] is True
    assert runtime_trace["writer_kb_payload_enabled_source"] == "default_local"
    assert writer_trace["enabled"] is True
    assert writer_trace["primary_path"] == "writer_kb_payload_v1"
    assert writer_trace["status"] == "structured_payload_used"
    assert int(writer_trace["payload_chunk_count"]) >= 1
    assert int(writer_trace["mid_sentence_cut_count"]) == 0
    assert writer_trace["fallback_is_primary"] is False
    assert writer_trace["payload_full_text_sent_to_writer"] is True
    assert writer_trace["payload_full_text_exposed_in_web_trace"] is False
