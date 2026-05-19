from __future__ import annotations

from tools import run_registry_focus_only_cleanup_hf3 as hf3


def test_admin_focus_only_browser_smoke_pass():
    payload = hf3.build_admin_focus_only_smoke(
        dashboard_resp={"status_code": 200, "body": {"chroma": {"status": "ok", "count": 247}}},
        registry_resp={
            "status_code": 200,
            "body": {
                "sources": [
                    {
                        "source_id": "123__кузница_духа",
                        "blocks_count": 247,
                        "delete_policy": {"state": "protected"},
                    }
                ]
            },
        },
        stats_resp={"status_code": 200, "body": {"total_blocks": 247}},
        expected_source_id="123__кузница_духа",
        expected_blocks=247,
    )
    assert payload["admin_focus_only_browser_smoke_passed"] is True
