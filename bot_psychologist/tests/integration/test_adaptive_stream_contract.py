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


def _parse_sse_events(sse_text: str) -> list[dict]:
    events: list[dict] = []
    for raw_event in [chunk for chunk in sse_text.split("\n\n") if chunk.strip()]:
        event_type = "message"
        data_lines: list[str] = []
        for line in raw_event.splitlines():
            line = line.strip()
            if line.startswith("event:"):
                event_type = line.replace("event:", "", 1).strip() or "message"
            elif line.startswith("data:"):
                data_lines.append(line.replace("data:", "", 1).strip())
        events.append({"type": event_type, "data_lines": data_lines})
    return events


async def _fake_stream_answer_tokens(*_args, **kwargs):
    on_complete = kwargs.get("on_complete")
    if callable(on_complete):
        on_complete(
            {
                "answer": "Полный ответ для проверки контракта.",
                "processing_time_seconds": 0.25,
                "metadata": {
                    "recommended_mode": "PRESENCE",
                    "sd_level": "GREEN",
                },
                "debug_trace": {
                    "turn_number": 7,
                    "recommended_mode": "PRESENCE",
                },
            }
        )
    for token in ["Полный ", "ответ ", "для ", "проверки ", "контракта."]:
        yield token


def _extract_done_payload(events: list[dict]) -> dict:
    for event in events:
        if event["type"] != "message":
            continue
        for data_line in event["data_lines"]:
            payload = json.loads(data_line)
            if payload.get("done") is True:
                return payload
    raise AssertionError("SSE done payload not found")


def _extract_token_text(events: list[dict]) -> str:
    tokens: list[str] = []
    for event in events:
        if event["type"] != "message":
            continue
        for data_line in event["data_lines"]:
            payload = json.loads(data_line)
            token = payload.get("token")
            if isinstance(token, str):
                tokens.append(token)
    return "".join(tokens)


def test_sse_events_use_blank_line_framing(monkeypatch) -> None:
    monkeypatch.setattr(routes, "stream_answer_tokens", _fake_stream_answer_tokens)
    monkeypatch.setattr(routes.config, "ENABLE_STREAMING", True, raising=False)

    with TestClient(app, base_url="http://localhost") as client:
        response = client.post(
            "/api/v1/questions/adaptive-stream",
            headers={"X-API-Key": "test-key-001"},
            json={"query": "тест", "user_id": "u1"},
        )

    assert response.status_code == 200
    assert "\n\n" in response.text
    assert len(_parse_sse_events(response.text)) >= 2


def test_done_payload_contains_non_empty_answer(monkeypatch) -> None:
    monkeypatch.setattr(routes, "stream_answer_tokens", _fake_stream_answer_tokens)
    monkeypatch.setattr(routes.config, "ENABLE_STREAMING", True, raising=False)

    with TestClient(app, base_url="http://localhost") as client:
        response = client.post(
            "/api/v1/questions/adaptive-stream",
            headers={"X-API-Key": "test-key-001"},
            json={"query": "тест", "user_id": "u1"},
        )

    events = _parse_sse_events(response.text)
    done = _extract_done_payload(events)
    assert done.get("done") is True
    assert isinstance(done.get("answer"), str)
    assert done["answer"].strip()


def test_trace_event_follows_done_in_debug_mode(monkeypatch) -> None:
    monkeypatch.setattr(routes, "stream_answer_tokens", _fake_stream_answer_tokens)
    monkeypatch.setattr(routes.config, "ENABLE_STREAMING", True, raising=False)

    with TestClient(app, base_url="http://localhost") as client:
        response = client.post(
            "/api/v1/questions/adaptive-stream",
            headers={"X-API-Key": "dev-key-001"},
            json={"query": "тест", "user_id": "u1", "debug": True},
        )

    events = _parse_sse_events(response.text)
    done_idx = None
    trace_idx = None

    for idx, event in enumerate(events):
        if done_idx is None and event["type"] == "message":
            for data_line in event["data_lines"]:
                payload = json.loads(data_line)
                if payload.get("done") is True:
                    done_idx = idx
                    break
        if trace_idx is None and event["type"] == "trace":
            trace_idx = idx

    assert done_idx is not None
    assert trace_idx is not None
    assert trace_idx > done_idx


def test_non_debug_stream_omits_trace_event(monkeypatch) -> None:
    monkeypatch.setattr(routes, "stream_answer_tokens", _fake_stream_answer_tokens)
    monkeypatch.setattr(routes.config, "ENABLE_STREAMING", True, raising=False)

    with TestClient(app, base_url="http://localhost") as client:
        response = client.post(
            "/api/v1/questions/adaptive-stream",
            headers={"X-API-Key": "test-key-001"},
            json={"query": "тест", "user_id": "u1", "debug": False},
        )

    events = _parse_sse_events(response.text)
    trace_events = [event for event in events if event["type"] == "trace"]
    assert trace_events == []


def test_token_events_precede_done_event(monkeypatch) -> None:
    monkeypatch.setattr(routes, "stream_answer_tokens", _fake_stream_answer_tokens)
    monkeypatch.setattr(routes.config, "ENABLE_STREAMING", True, raising=False)

    with TestClient(app, base_url="http://localhost") as client:
        response = client.post(
            "/api/v1/questions/adaptive-stream",
            headers={"X-API-Key": "test-key-001"},
            json={"query": "тест", "user_id": "u1"},
        )

    events = _parse_sse_events(response.text)
    done_idx = None
    token_indices: list[int] = []

    for idx, event in enumerate(events):
        if event["type"] != "message":
            continue
        for data_line in event["data_lines"]:
            payload = json.loads(data_line)
            if "token" in payload:
                token_indices.append(idx)
            if payload.get("done") is True and done_idx is None:
                done_idx = idx

    assert done_idx is not None
    assert token_indices
    assert all(index < done_idx for index in token_indices)


def test_done_answer_is_not_shorter_than_accumulated_tokens(monkeypatch) -> None:
    monkeypatch.setattr(routes, "stream_answer_tokens", _fake_stream_answer_tokens)
    monkeypatch.setattr(routes.config, "ENABLE_STREAMING", True, raising=False)

    with TestClient(app, base_url="http://localhost") as client:
        response = client.post(
            "/api/v1/questions/adaptive-stream",
            headers={"X-API-Key": "test-key-001"},
            json={"query": "тест", "user_id": "u1"},
        )

    events = _parse_sse_events(response.text)
    done = _extract_done_payload(events)
    token_text = _extract_token_text(events)
    done_answer = str(done.get("answer") or "")

    assert token_text
    assert done_answer
    assert len(done_answer) >= len(token_text)
