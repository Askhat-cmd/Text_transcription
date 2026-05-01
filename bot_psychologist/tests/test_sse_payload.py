from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api import routes
from api.main import app


def _collect_sse_events(response_text: str) -> list[dict]:
    events: list[dict] = []
    blocks = [chunk for chunk in response_text.split("\n\n") if chunk.strip()]
    for block in blocks:
        event_type = "message"
        payload: dict | None = None
        for line in block.splitlines():
            line = line.strip()
            if line.startswith("event:"):
                event_type = line.replace("event:", "", 1).strip() or "message"
            elif line.startswith("data:"):
                raw = line.replace("data:", "", 1).strip()
                if not raw:
                    continue
                try:
                    payload = json.loads(raw)
                except json.JSONDecodeError:
                    payload = None
        if payload is not None:
            events.append({"type": event_type, "data": payload})
    return events


def _fake_stream_result(*_args, **_kwargs) -> dict:
    return {
        "answer": "Осознанность помогает замечать эмоции и возвращаться в настоящий момент.",
        "processing_time_seconds": 0.05,
        "metadata": {"recommended_mode": "PRESENCE", "sd_level": "GREEN"},
        "status": "success",
        "sources": [],
        "debug_trace": {
            "hybrid_query": "X" * 6000,
            "llm_calls": [],
            "pipeline_stages": [],
        },
    }


def test_done_event_has_no_trace_field(monkeypatch) -> None:
    monkeypatch.setattr(routes, "answer_question_adaptive", _fake_stream_result)
    monkeypatch.setattr(routes.config, "ENABLE_STREAMING", True, raising=False)

    with TestClient(app, base_url="http://localhost") as client:
        response = client.post(
            "/api/v1/questions/adaptive-stream",
            json={"query": "Что такое осознанность?", "user_id": "test_user"},
            headers={"X-API-Key": "test-key-001"},
        )

    events = _collect_sse_events(response.text)
    done_events = [e for e in events if e["data"].get("done") is True]
    assert len(done_events) == 1
    done_data = done_events[0]["data"]
    assert "trace" not in done_data
    assert "answer" in done_data
    assert "answer_fallback" in done_data
    assert done_data["answer"] == done_data["answer_fallback"]
    assert "latency_ms" in done_data
    assert done_data.get("session_id")
    assert done_data.get("conversation_id")


def test_done_event_size_under_2kb(monkeypatch) -> None:
    monkeypatch.setattr(routes, "answer_question_adaptive", _fake_stream_result)
    monkeypatch.setattr(routes.config, "ENABLE_STREAMING", True, raising=False)

    with TestClient(app, base_url="http://localhost") as client:
        response = client.post(
            "/api/v1/questions/adaptive-stream",
            json={"query": "Проверка размера done payload", "user_id": "test_user"},
            headers={"X-API-Key": "test-key-001"},
        )

    events = _collect_sse_events(response.text)
    done_events = [e for e in events if e["data"].get("done") is True]
    assert len(done_events) == 1
    done_raw = json.dumps(done_events[0]["data"], ensure_ascii=False)
    assert len(done_raw.encode("utf-8")) < 2048


def test_trace_sent_as_separate_event_when_debug(monkeypatch) -> None:
    monkeypatch.setattr(routes, "answer_question_adaptive", _fake_stream_result)
    monkeypatch.setattr(routes.config, "ENABLE_STREAMING", True, raising=False)

    with TestClient(app, base_url="http://localhost") as client:
        response = client.post(
            "/api/v1/questions/adaptive-stream",
            json={"query": "Тест", "user_id": "test_user", "debug": True},
            headers={"X-API-Key": "dev-key-001"},
        )

    events = _collect_sse_events(response.text)
    trace_events = [e for e in events if e["type"] == "trace"]
    done_events = [e for e in events if e["data"].get("done") is True]

    assert len(done_events) == 1
    assert "trace" not in done_events[0]["data"]
    assert len(trace_events) == 1
    assert "done" not in trace_events[0]["data"]


def test_trace_persisted_under_trace_session_id_for_llm_payload(monkeypatch) -> None:
    trace_session_id = "trace-session-xyz"

    def _fake_result(*_args, **_kwargs) -> dict:
        return {
            "answer": "ok",
            "processing_time_seconds": 0.01,
            "metadata": {"recommended_mode": "PRESENCE"},
            "status": "success",
            "debug_trace": {
                "session_id": trace_session_id,
                "turn_number": 1,
                "recommended_mode": "PRESENCE",
                "llm_calls": [
                    {
                        "step": "answer",
                        "model": "gpt-5-mini",
                        "duration_ms": 50,
                        "system_prompt_preview": "sys",
                        "user_prompt_preview": "usr",
                    }
                ],
            },
        }

    monkeypatch.setattr(routes, "answer_question_adaptive", _fake_result)
    monkeypatch.setattr(routes.config, "ENABLE_STREAMING", True, raising=False)

    with TestClient(app, base_url="http://localhost") as client:
        stream_resp = client.post(
            "/api/v1/questions/adaptive-stream",
            json={"query": "Тест", "user_id": "request_user", "debug": True},
            headers={"X-API-Key": "dev-key-001"},
        )
        assert stream_resp.status_code == 200

        payload_resp = client.get(
            f"/api/debug/session/{trace_session_id}/llm-payload?format=flat",
            headers={"X-API-Key": "dev-key-001"},
        )

    assert payload_resp.status_code == 200
    data = payload_resp.json()
    assert data.get("session_id") == trace_session_id
    assert isinstance(data.get("llm_calls"), list)
    assert len(data["llm_calls"]) == 1
