from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.main import app
from api import routes
from api.session_store import get_session_store


def _extract_done_payload(sse_text: str) -> dict:
    events = [chunk for chunk in sse_text.split("\n\n") if chunk.strip()]
    payloads: list[dict] = []
    for event in events:
        for line in event.splitlines():
            if not line.startswith("data:"):
                continue
            data = line.replace("data:", "", 1).strip()
            if not data:
                continue
            payloads.append(json.loads(data))
    for payload in reversed(payloads):
        if payload.get("done") is True:
            return payload
    raise AssertionError("SSE done payload not found")


def _reset_store() -> None:
    store = get_session_store()
    with store._lock:  # type: ignore[attr-defined]
        store._sessions.clear()  # type: ignore[attr-defined]
        store._blobs.clear()  # type: ignore[attr-defined]


def test_stream_debug_contract_omits_sd_when_runtime_disabled(monkeypatch) -> None:
    _reset_store()
    monkeypatch.setenv("DISABLE_SD_RUNTIME", "true")
    monkeypatch.setattr(routes.config, "ENABLE_STREAMING", True, raising=False)

    def _fake_answer_question_adaptive(*_args, **_kwargs):
        return {
            "status": "success",
            "answer": "короткий тестовый ответ",
            "state_analysis": {"primary_state": "curious"},
            "processing_time_seconds": 0.01,
            "metadata": {"recommended_mode": "PRESENCE", "sd_level": "GREEN"},
            "debug_trace": {
                "sd_classification": {"primary": "GREEN"},
                "sd_detail": {"primary": "GREEN"},
                "sd_level": "GREEN",
                "llm_calls": [],
            },
        }

    monkeypatch.setattr(routes, "answer_question_adaptive", _fake_answer_question_adaptive)

    with TestClient(app, base_url="http://localhost") as client:
        response = client.post(
            "/api/v1/questions/adaptive-stream",
            headers={"X-API-Key": "dev-key-001"},
            json={"query": "тест", "user_id": "u1"},
        )

    assert response.status_code == 200
    done = _extract_done_payload(response.text)
    assert done["done"] is True
    assert "sd_level" not in done
    trace = done.get("trace")
    assert isinstance(trace, dict)
    assert "sd_classification" not in trace
    assert "sd_detail" not in trace
    assert "sd_level" not in trace
