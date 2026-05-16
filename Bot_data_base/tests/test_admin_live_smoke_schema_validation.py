from __future__ import annotations

from review.admin_live_smoke import evaluate_admin_contract


def _base_checks() -> dict:
    return {
        "/api/status": {"ok": True, "status_code": 200, "body": {"ok": True}, "error": None},
        "/api/registry": {
            "ok": True,
            "status_code": 200,
            "body": {"sources": [{"source_id": "123__кузница_духа", "status": "done", "blocks_count": 247}]},
            "error": None,
        },
        "/api/dashboard": {
            "ok": True,
            "status_code": 200,
            "body": {"blocks": {"production_total": 247}, "chroma": {"count": 247}},
            "error": None,
        },
        "/api/dashboard/": {
            "ok": True,
            "status_code": 200,
            "body": {"blocks": {"production_total": 247}, "chroma": {"count": 247}},
            "error": None,
        },
    }


def test_non_json_dashboard_payload_is_schema_blocker() -> None:
    checks = _base_checks()
    checks["/api/dashboard"]["body"] = "not-json-object"
    result = evaluate_admin_contract(
        api_checks=checks,
        expected_source_id="123__кузница_духа",
        expected_blocks_total=247,
    )
    assert result["admin_runtime_status"] == "failed_schema_validation"
    assert result["admin_consistency_passed"] is False
    assert "dashboard_payload_invalid" in result["issues"]


def test_registry_focus_blocks_mismatch_is_schema_blocker() -> None:
    checks = _base_checks()
    checks["/api/registry"]["body"] = {"sources": [{"source_id": "123__кузница_духа", "status": "done", "blocks_count": 246}]}
    result = evaluate_admin_contract(
        api_checks=checks,
        expected_source_id="123__кузница_духа",
        expected_blocks_total=247,
    )
    assert result["admin_runtime_status"] == "failed_schema_validation"
    assert result["admin_consistency_passed"] is False
    assert "registry_focus_blocks_mismatch" in result["issues"]


def test_dashboard_empty_payload_is_schema_blocker() -> None:
    checks = _base_checks()
    checks["/api/dashboard"]["body"] = {}
    result = evaluate_admin_contract(
        api_checks=checks,
        expected_source_id="123__кузница_духа",
        expected_blocks_total=247,
    )
    assert result["admin_runtime_status"] == "failed_schema_validation"
    assert result["admin_consistency_passed"] is False
    assert "dashboard_payload_invalid" in result["issues"]
