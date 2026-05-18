from __future__ import annotations

from tools import run_admin_browser_visible_smoke_hf1 as smoke


def test_admin_browser_visible_smoke_passes_with_expected_contract(monkeypatch):
    def fake_http(url: str, **kwargs):
        if url.endswith("/api/registry/"):
            return {
                "ok": True,
                "status_code": 200,
                "body": {
                    "sources": [
                        {"source_id": "123__кузница_духа", "blocks_count": 247, "status": "done"}
                    ]
                },
                "error": None,
            }
        if url.endswith("/api/dashboard"):
            return {
                "ok": True,
                "status_code": 200,
                "body": {"chroma": {"status": "ok", "count": 247}},
                "error": None,
            }
        if url.endswith("/api/registry/stats"):
            return {
                "ok": True,
                "status_code": 200,
                "body": {"chroma_total": 247},
                "error": None,
            }
        return {"ok": True, "status_code": 200, "body": "ok", "error": None}

    monkeypatch.setattr(smoke, "_http_request", fake_http)

    payload = smoke.run_browser_visible_smoke(
        source_prd="PRD-046.1.21-HF1",
        admin_base_url="http://127.0.0.1:8003",
        expected_source_id="123__кузница_духа",
        expected_blocks=247,
    )

    assert payload["admin_browser_visible_smoke_passed"] is True
    assert payload["issues"] == []
