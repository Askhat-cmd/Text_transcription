from __future__ import annotations

from review.post_apply_quality_gate import build_admin_api_runtime_smoke, build_quality_gate_snapshot


def _offline_fetch(_: str) -> dict:
    return {"ok": False, "status_code": None, "body": None, "error": "connection refused"}


def _online_fetch(url: str) -> dict:
    if url.endswith("/api/status"):
        return {"ok": True, "status_code": 200, "body": {"ok": True}, "error": None}
    if url.endswith("/api/registry"):
        return {
            "ok": True,
            "status_code": 200,
            "body": {"sources": [{"source_id": "123__кузница_духа", "status": "done", "blocks_count": 247}]},
            "error": None,
        }
    if url.endswith("/api/dashboard") or url.endswith("/api/dashboard/"):
        return {"ok": True, "status_code": 200, "body": {"schema_version": "botdb_dashboard_summary_v1"}, "error": None}
    return {"ok": False, "status_code": 404, "body": None, "error": "not found"}


def _base_gate_payloads() -> dict:
    return {
        "data_consistency": {"data_consistency_passed": True},
        "apply_route_consistency": {"apply_route_consistency_passed": True},
        "retrieval_quality": {"retrieval_quality_passed": True},
        "writer_policy": {"writer_kb_policy_passed": True},
        "no_mutation": {"all_blocks_merged_mutated": False, "registry_mutated": False},
    }


def test_connection_refused_never_passes_admin_consistency() -> None:
    smoke = build_admin_api_runtime_smoke(
        admin_base_url="http://127.0.0.1:8000",
        expected_source_id="123__кузница_духа",
        expected_blocks_total=247,
        allow_offline_admin_checks=False,
        require_admin_api=True,
        http_get=_offline_fetch,
    )
    assert smoke["admin_runtime_status"] == "blocked_admin_api_unavailable"
    assert smoke["admin_consistency_passed"] is False


def test_allow_offline_sets_skipped_but_not_diagnostic_ready() -> None:
    smoke = build_admin_api_runtime_smoke(
        admin_base_url="http://127.0.0.1:8000",
        expected_source_id="123__кузница_духа",
        expected_blocks_total=247,
        allow_offline_admin_checks=True,
        require_admin_api=True,
        http_get=_offline_fetch,
    )
    assert smoke["admin_runtime_status"] == "skipped_offline_explicit"
    assert smoke["admin_consistency_passed"] is False

    payloads = _base_gate_payloads()
    snapshot = build_quality_gate_snapshot(
        source_prd="PRD-046.0.7.2",
        data_consistency=payloads["data_consistency"],
        apply_route_consistency=payloads["apply_route_consistency"],
        retrieval_quality=payloads["retrieval_quality"],
        writer_policy=payloads["writer_policy"],
        admin_runtime=smoke,
        no_mutation_proof=payloads["no_mutation"],
    )
    assert snapshot["quality_gate_passed"] is False
    assert snapshot["diagnostic_center_ready"] is False


def test_slash_and_noslash_dashboard_checked() -> None:
    smoke = build_admin_api_runtime_smoke(
        admin_base_url="http://127.0.0.1:8000",
        expected_source_id="123__кузница_духа",
        expected_blocks_total=247,
        allow_offline_admin_checks=False,
        require_admin_api=True,
        http_get=_online_fetch,
    )
    assert smoke["admin_runtime_status"] == "passed"
    assert smoke["admin_consistency_passed"] is True
    assert "/api/dashboard" in smoke["api_checks"]
    assert "/api/dashboard/" in smoke["api_checks"]
