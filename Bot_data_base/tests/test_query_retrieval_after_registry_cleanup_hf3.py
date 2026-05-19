from __future__ import annotations

from pathlib import Path

from tools import run_registry_focus_only_cleanup_hf3 as hf3


def test_query_retrieval_after_registry_cleanup_pass(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        hf3,
        "run_query_acceptance",
        lambda **kwargs: {
            "botdb_api_query_status": 200,
            "rag_hits_count": 3,
            "semantic_fallback_used": False,
            "botdb_circuit_open": False,
            "query_http_503_chromadb_unavailable": False,
        },
    )
    monkeypatch.setattr(
        hf3,
        "run_bot_retrieval_smoke",
        lambda **kwargs: {
            "queries": [
                {
                    "retrieval_source_used": "api",
                    "bot_db_circuit_open": False,
                }
            ]
        },
    )
    payload = hf3.build_query_retrieval_regression(repo_root=tmp_path, admin_base_url="http://127.0.0.1:8003")
    assert payload["query_retrieval_regression_passed"] is True
