from pathlib import Path
import sys

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.main import app
from api.session_store import get_session_store


DEV_HEADERS = {"X-API-Key": "dev-key-001"}


def _reset_store() -> None:
    store = get_session_store()
    with store._lock:  # type: ignore[attr-defined]
        store._sessions.clear()  # type: ignore[attr-defined]
        store._blobs.clear()  # type: ignore[attr-defined]


def test_metrics_include_session_token_decomposition() -> None:
    _reset_store()
    store = get_session_store()

    store.append_trace(
        "s-metrics",
        {
            "turn_number": 1,
            "tokens_prompt": 100,
            "tokens_completion": 40,
            "tokens_total": 140,
            "estimated_cost_usd": 0.0012,
            "total_duration_ms": 1200,
            "fast_path": False,
            "anomalies": [{"code": "SLOW_STAGE", "severity": "warn"}],
        },
    )
    store.append_trace(
        "s-metrics",
        {
            "turn_number": 2,
            "llm_calls": [
                {
                    "step": "answer",
                    "tokens_prompt": 120,
                    "tokens_completion": 55,
                    "tokens_total": 175,
                }
            ],
            "estimated_cost_usd": 0.0015,
            "total_duration_ms": 1500,
            "fast_path": True,
            "anomalies": [],
        },
    )

    with TestClient(app, base_url="http://localhost") as client:
        response = client.get("/api/debug/session/s-metrics/metrics", headers=DEV_HEADERS)

    assert response.status_code == 200
    data = response.json()
    assert data["total_turns"] == 2
    assert data["total_prompt_tokens"] == 220
    assert data["total_completion_tokens"] == 95
    assert data["total_tokens"] == 315
    assert data["total_cost_usd"] == 0.0027


def test_traces_compact_format_strips_heavy_fields() -> None:
    _reset_store()
    store = get_session_store()
    store.append_trace(
        "s-compact",
        {
            "turn_number": 1,
            "summary_text": "very long summary",
            "context_written": "large memory write",
            "memory_turns_content": [{"turn_index": 1, "role": "user", "text_preview": "hi"}],
            "semantic_hits_detail": [{"block_id": "b1", "score": 0.77, "text_preview": "x"}],
            "pipeline_stages": [
                {"name": "state_classifier", "duration_ms": 10, "skipped": False},
                {"name": "sd_classifier", "duration_ms": 0, "skipped": True},
            ],
            "llm_calls": [
                {
                    "step": "answer",
                    "model": "gpt-5-mini",
                    "duration_ms": 333,
                    "tokens_total": 500,
                    "system_prompt_preview": "sys",
                    "user_prompt_preview": "usr",
                }
            ],
        },
    )

    with TestClient(app, base_url="http://localhost") as client:
        response = client.get("/api/debug/session/s-compact/traces?format=compact", headers=DEV_HEADERS)

    assert response.status_code == 200
    data = response.json()
    assert data["format"] == "compact"
    trace = data["traces"][0]
    assert "summary_text" not in trace
    assert "context_written" not in trace
    assert "memory_turns_content" not in trace
    assert "semantic_hits_detail" not in trace
    assert all(not stage.get("skipped") for stage in trace.get("pipeline_stages", []))
    assert "system_prompt_preview" not in trace["llm_calls"][0]
    assert trace["llm_calls"][0]["step"] == "answer"
