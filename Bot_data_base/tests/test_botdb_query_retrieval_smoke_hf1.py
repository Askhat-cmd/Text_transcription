from __future__ import annotations

from tools import run_live_botdb_chroma_registry_audit_hf1 as runner


def test_botdb_query_retrieval_smoke_detects_no_fallback(monkeypatch):
    def fake_http_call(base_url, method, endpoint, body):
        return {
            "ok": True,
            "status_code": 200,
            "body": {"chunks": [{"chunk_id": "1"}, {"chunk_id": "2"}], "total_found": 2},
            "error": None,
        }

    monkeypatch.setattr(runner, "_http_call", fake_http_call)

    payload = runner._build_bot_retrieval_smoke("http://127.0.0.1:8003")

    assert payload["botdb_api_query_status"] == 200
    assert payload["semantic_fallback_used"] is False
    assert payload["botdb_circuit_open"] is False
    assert payload["rag_hits_count"] == 2
