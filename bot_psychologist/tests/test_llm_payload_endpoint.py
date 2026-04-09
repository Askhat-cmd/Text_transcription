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


def _seed_trace(session_id: str, *, user_prompt: str, turn_number: int = 3, summary_pending_turn=None) -> None:
    store = get_session_store()
    store.set_blob(f"{session_id}:sys", "SYSTEM PROMPT TEXT")
    store.set_blob(f"{session_id}:user", user_prompt)
    store.set_blob(f"{session_id}:mem", "MEMORY SNAPSHOT TEXT")

    trace = {
        "turn_number": turn_number,
        "recommended_mode": "PRESENCE",
        "user_state": "curious",
        "hybrid_query_preview": "query preview",
        "hybrid_query_text": "query preview full",
        "hybrid_query_len": 18,
        "context_mode": "summary",
        "summary_used": True,
        "summary_text": "summary from trace",
        "summary_pending_turn": summary_pending_turn,
        "chunks_after_filter": [
            {"block_id": "b1", "title": "Block 1", "score_final": 0.77},
        ],
        "memory_snapshot_blob_id": f"{session_id}:mem",
        "llm_calls": [
            {
                "step": "answer",
                "model": "gpt-5-mini",
                "tokens_prompt": 10,
                "tokens_completion": 20,
                "tokens_total": 30,
                "duration_ms": 123,
                "system_prompt_blob_id": f"{session_id}:sys",
                "user_prompt_blob_id": f"{session_id}:user",
                "response_preview": "response preview",
            }
        ],
    }
    store.append_trace(session_id, trace)


def test_llm_payload_endpoint_returns_structured_payload_by_default() -> None:
    _reset_store()
    user_prompt = """[CONVERSATION SUMMARY]\nsummary in prompt\n\n[RECENT DIALOG]\n- user: hi\n- bot: hello\n\nМАТЕРИАЛ ИЗ ЛЕКЦИЙ:\n--- BLOCK 1 ---\ncontent\n\nВОПРОС ПОЛЬЗОВАТЕЛЯ:\nwhat now?\n"""
    _seed_trace("s1", user_prompt=user_prompt, turn_number=5)

    with TestClient(app, base_url="http://localhost") as client:
        response = client.get("/api/debug/session/s1/llm-payload", headers=DEV_HEADERS)

    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "s1"
    assert data["turn_index"] == 5
    assert data["context_mode"] in {"summary", "full"}
    assert isinstance(data["sections"], list)
    names = {section["name"] for section in data["sections"]}
    assert "CORE_IDENTITY" in names
    assert "RECENT_DIALOG" in names
    assert "TASK_INSTRUCTION" in names
    assert "diagnostics" in data
    assert data["diagnostics"]["hybridquery_len"] >= 0


def test_llm_payload_endpoint_supports_flat_format() -> None:
    _reset_store()
    user_prompt = "ВОПРОС ПОЛЬЗОВАТЕЛЯ:\nflat"
    _seed_trace("s2", user_prompt=user_prompt, turn_number=2)

    with TestClient(app, base_url="http://localhost") as client:
        response = client.get("/api/debug/session/s2/llm-payload?format=flat", headers=DEV_HEADERS)

    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "s2"
    assert "llm_calls" in data
    assert data["llm_calls"][0]["system_prompt"] == "SYSTEM PROMPT TEXT"
    assert data["llm_calls"][0]["user_prompt"].startswith("ВОПРОС")


def test_llm_payload_diagnostics_summary_lag_when_pending_turn_matches() -> None:
    _reset_store()
    user_prompt = """[RECENT DIALOG]\n- user: hi\n\nМАТЕРИАЛ ИЗ ЛЕКЦИЙ:\nblock\n\nВОПРОС ПОЛЬЗОВАТЕЛЯ:\nq"""
    _seed_trace("s3", user_prompt=user_prompt, turn_number=7, summary_pending_turn=7)

    with TestClient(app, base_url="http://localhost") as client:
        response = client.get("/api/debug/session/s3/llm-payload", headers=DEV_HEADERS)

    assert response.status_code == 200
    data = response.json()
    assert data["diagnostics"]["summary_lag"] is True
