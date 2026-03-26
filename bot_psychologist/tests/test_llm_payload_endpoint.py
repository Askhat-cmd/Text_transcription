from pathlib import Path
import sys

from fastapi.testclient import TestClient

# Keep imports stable when pytest is launched from monorepo root.
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


def test_llm_payload_endpoint_returns_latest_trace_payload():
    _reset_store()
    store = get_session_store()

    store.set_blob("s1:sys", "SYSTEM PROMPT TEXT")
    store.set_blob("s1:user", "USER PROMPT TEXT")
    store.set_blob("s1:mem", "MEMORY SNAPSHOT TEXT")

    store.append_trace(
        "s1",
        {
            "turn_number": 3,
            "recommended_mode": "PRESENCE",
            "sd_level": "GREEN",
            "user_state": "curious",
            "hybrid_query_preview": "query preview",
            "chunks_after_filter": [{"block_id": "b1"}],
            "memory_snapshot_blob_id": "s1:mem",
            "llm_calls": [
                {
                    "step": "answer",
                    "model": "gpt-5-mini",
                    "tokens_prompt": 10,
                    "tokens_completion": 20,
                    "tokens_total": 30,
                    "duration_ms": 123,
                    "system_prompt_blob_id": "s1:sys",
                    "user_prompt_blob_id": "s1:user",
                    "response_preview": "response preview",
                }
            ],
        },
    )

    with TestClient(app, base_url="http://localhost") as client:
        response = client.get("/api/debug/session/s1/llm-payload", headers=DEV_HEADERS)

    assert response.status_code == 200
    payload = response.json()
    assert payload["session_id"] == "s1"
    assert payload["turn_number"] == 3
    assert payload["chunks_count"] == 1
    assert payload["llm_calls"][0]["system_prompt"] == "SYSTEM PROMPT TEXT"
    assert payload["llm_calls"][0]["user_prompt"] == "USER PROMPT TEXT"
    assert payload["memory_snapshot"] == "MEMORY SNAPSHOT TEXT"


def test_llm_payload_endpoint_404_when_no_llm_calls():
    _reset_store()
    store = get_session_store()
    store.append_trace("s2", {"turn_number": 1, "llm_calls": []})

    with TestClient(app, base_url="http://localhost") as client:
        response = client.get("/api/debug/session/s2/llm-payload", headers=DEV_HEADERS)

    assert response.status_code == 404
    assert response.json()["detail"] == "No LLM payload for this session"
