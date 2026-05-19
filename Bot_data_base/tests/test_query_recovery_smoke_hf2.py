from __future__ import annotations

from pathlib import Path

from tools import run_botdb_live_recovery_hf2 as runner


def test_query_recovery_smoke_pass(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        runner,
        "run_query_acceptance",
        lambda **kwargs: {
            "botdb_api_query_status": 200,
            "rag_hits_count": 2,
            "query_http_503_chromadb_unavailable": False,
            "botdb_query_route_fallback_used": False,
            "runtime_fallback_used": False,
        },
    )
    payload = runner._query_recovery_smoke(tmp_path, "http://127.0.0.1:8003", tmp_path)
    assert payload["query_http_200"] is True
    assert payload["rag_hits_count"] == 2
    assert payload["query_recovery_status"] == "passed"
