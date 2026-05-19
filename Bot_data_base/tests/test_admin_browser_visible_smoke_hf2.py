from __future__ import annotations

from tools import run_admin_browser_visible_smoke_hf2 as smoke_tool


def test_admin_browser_visible_smoke_pass(monkeypatch):
    monkeypatch.setattr(
        smoke_tool,
        "run_acceptance",
        lambda **kwargs: {
            "dashboard_page_http_200": True,
            "registry_page_http_200": True,
            "registry_stats_http_200": True,
            "dashboard_chroma_status": "ok",
            "dashboard_chroma_count": 247,
            "focus_source_visible": True,
            "focus_source_protected": True,
            "admin_browser_acceptance_passed": True,
            "registry_global_error_http_500": False,
            "issues": [],
            "runtime_fallback_used": False,
            "primary_base_url": "http://127.0.0.1:8003",
            "effective_base_url": "http://127.0.0.1:8003",
        },
    )
    payload = smoke_tool.run_visible_smoke(
        repo_root=".",
        admin_base_url="http://127.0.0.1:8003",
        expected_source_id="123__кузница_духа",
        expected_blocks=247,
    )
    assert payload["admin_browser_visible_smoke_passed"] is True
    assert payload["dashboard_chroma_status"] == "ok"
