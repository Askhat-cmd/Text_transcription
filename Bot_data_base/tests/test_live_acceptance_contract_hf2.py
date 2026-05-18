from __future__ import annotations

from tools import run_admin_browser_acceptance_hf2 as tool


def test_live_acceptance_contract_passes(monkeypatch):
    def fake_http(url: str, **kwargs):
        if url.endswith("/api/dashboard"):
            return {"ok": True, "status_code": 200, "body": {"chroma": {"status": "ok", "count": 247}}, "error": None}
        if url.endswith("/api/registry/"):
            return {
                "ok": True,
                "status_code": 200,
                "body": {"sources": [{"source_id": "123__кузница_духа", "blocks_count": 247, "delete_policy": {"state": "protected"}, "delete_allowed": False}]},
                "error": None,
            }
        if url.endswith("/api/registry/stats"):
            return {"ok": True, "status_code": 200, "body": {"chroma_status": "ok", "chroma_total": 247}, "error": None}
        return {"ok": True, "status_code": 200, "body": "ok", "error": None}

    monkeypatch.setattr(tool, "_http_json", fake_http)
    payload = tool.run_acceptance(
        repo_root=".",
        admin_base_url="http://127.0.0.1:8003",
        expected_source_id="123__кузница_духа",
        expected_blocks=247,
    )
    assert payload["admin_browser_acceptance_passed"] is True
