from __future__ import annotations

from pathlib import Path

from tools import run_botdb_live_recovery_hf2 as runner


def test_bot_runtime_retrieval_smoke_pass(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        runner,
        "run_bot_retrieval_smoke",
        lambda **kwargs: {
            "fallback_used": False,
            "circuit_breaker_open": False,
            "queries": [
                {
                    "retrieval_source_used": "api",
                    "bot_db_circuit_open": False,
                    "bot_db_last_status_code": 200,
                    "knowledge_hits_count": 2,
                }
            ],
        },
    )
    payload = runner._bot_runtime_retrieval_smoke("http://127.0.0.1:8003", tmp_path)
    assert payload["bot_runtime_retrieval_status"] == "passed"
    assert payload["semantic_fallback_used"] is False
    assert payload["botdb_circuit_open"] is False
