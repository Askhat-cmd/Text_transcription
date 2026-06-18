from __future__ import annotations

from pathlib import Path
import sys

TESTS_ROOT = Path(__file__).resolve().parents[1]
if str(TESTS_ROOT) not in sys.path:
    sys.path.insert(0, str(TESTS_ROOT))

from tools.run_prd_047_25_overlay_payload_live_evidence import (
    NEXT_PRD_PATH_B,
    build_live_evidence_cases,
    build_overlay_payload_alignment_report,
    run_runtime_duality_audit,
    summarize_live_evidence_results,
    validate_case_dataset,
)


def _live_export(
    case_id: str,
    *,
    payload_primary: bool = True,
    payload_count: int = 1,
    overlay_would_help: bool = False,
    overlay_enabled: bool = True,
    current_turn_status: str = "clean",
    retrieval_primary: str = "current_turn_focus_v1",
    response_status: int = 200,
    debug_status: int = 200,
    direct_answer_success: bool = True,
) -> dict:
    writer_primary = "writer_kb_payload_v1" if payload_primary else "legacy_semantic_hits_fallback_v1"
    return {
        "case_id": case_id,
        "response_status": response_status,
        "debug_status": debug_status,
        "writer_kb_payload_trace": {
            "primary_path": writer_primary,
            "payload_chunk_count": payload_count,
            "fallback_is_primary": not payload_primary,
        },
        "overlay_shadow_trace": {
            "enabled": overlay_enabled,
            "would_help": overlay_would_help,
            "used_for_writer": False,
            "used_for_retrieval_execution": False,
            "used_for_final_answer": False,
        },
        "retrieval_query_build_trace": {
            "primary_path": retrieval_primary,
            "current_turn_focus_status": current_turn_status,
            "duplicate_fragment_count": 0,
            "query_truncated_mid_word": False,
            "previous_user_query_included": False,
        },
        "quality_flags": {
            "direct_answer_success": direct_answer_success,
            "current_turn_focus_clean": True,
        },
        "safety_flags": {
            "raw_kb_dump_detected": False,
            "unsafe_practice_detected": False,
            "diagnostic_overclaim_detected": False,
        },
        "internal_leak_detected": False,
    }


def test_validate_case_dataset_has_required_mix() -> None:
    report = validate_case_dataset(build_live_evidence_cases())
    assert report["status"] == "passed"
    assert report["case_count"] == 20
    assert report["category_counts"]["direct_kb_concepts"] >= 4
    assert report["category_counts"]["elliptical_followup"] == 2


def test_runtime_duality_audit_marks_emergency_fallback_as_warning(tmp_path: Path) -> None:
    runtime_effective = {
        "runtime_entrypoint": "multiagent_adapter",
        "writer_kb_payload": {
            "primary_path": "writer_kb_payload_v1",
            "legacy_fallback_role": "emergency_only",
            "fallback_warning_required": True,
        },
        "trace": {
            "runtime_config_trace": {
                "retrieval_current_turn_focus_enabled": True,
                "overlay_shadow_trace_enabled": True,
            }
        },
    }
    route_inventory = {
        "stream_endpoint_present": True,
        "non_stream_endpoint_present": True,
        "web_ui_uses_stream_adaptive_answer": True,
        "runtime_entrypoint_multiagent_adapter_declared": True,
        "legacy_cascade_physically_removed_declared": True,
    }
    live_exports = [_live_export("E25-001")]

    report = run_runtime_duality_audit(
        runtime_effective=runtime_effective,
        route_inventory=route_inventory,
        live_exports=live_exports,
        out_dir=tmp_path,
    )

    assert report["status"] == "passed_with_warning"
    assert report["writer_kb_payload_primary"] is True
    assert report["legacy_query_builder_primary"] is False
    assert report["overlay_apply_enabled"] is False
    assert "legacy_semantic_hits_fallback_emergency_only" in report["warnings"]


def test_overlay_alignment_flags_noise_and_missing_expected(tmp_path: Path) -> None:
    cases = [
        {
            "case_id": "E25-001",
            "overlay_shadow_expected": False,
            "kb_payload_expected": True,
            "category": "direct_kb_concepts",
            "query": "Что такое Нейросталкинг?",
        },
        {
            "case_id": "E25-003",
            "overlay_shadow_expected": True,
            "kb_payload_expected": True,
            "category": "direct_kb_concepts",
            "query": "Что такое программа «Несовершенное Я»?",
        },
    ]
    exports = [
        _live_export("E25-001", overlay_would_help=True, payload_count=1),
        _live_export("E25-003", overlay_would_help=False, payload_count=1),
    ]

    report = build_overlay_payload_alignment_report(cases=cases, live_exports=exports, out_dir=tmp_path)

    assert report["false_positive_count"] == 1
    assert report["missing_where_expected_count"] == 1
    classifications = {item["case_id"]: item["classification"] for item in report["classifications"]}
    assert classifications["E25-001"] == "overlay_noise_possible"
    assert classifications["E25-003"] == "overlay_missing_where_expected"


def test_summary_recommends_overlay_noise_repair_when_false_positives_high(tmp_path: Path) -> None:
    cases = build_live_evidence_cases()
    exports = []
    for case in cases:
        overlay_would_help = bool(case.get("overlay_shadow_expected", False))
        if case["case_id"] in {"E25-001", "E25-002", "E25-004"}:
            overlay_would_help = True
        payload_count = 1 if case["case_id"] not in {"E25-017", "E25-018"} else 0
        exports.append(
            _live_export(
                case["case_id"],
                payload_count=payload_count,
                overlay_would_help=overlay_would_help,
                current_turn_status=str(case.get("current_turn_focus_expected", "clean")),
            )
        )

    alignment = build_overlay_payload_alignment_report(cases=cases, live_exports=exports, out_dir=tmp_path)
    duality = {
        "status": "passed_with_warning",
        "warnings": ["legacy_semantic_hits_fallback_emergency_only"],
    }
    retrieval_health = {"status": "passed", "warnings": []}

    report = summarize_live_evidence_results(
        cases=cases,
        live_exports=exports,
        alignment_report=alignment,
        duality_audit=duality,
        retrieval_health_report=retrieval_health,
        out_dir=tmp_path,
    )

    assert report["status"] == "passed_with_warning"
    assert report["kb_payload_primary_rate"] >= 0.8
    assert report["legacy_query_builder_primary_count"] == 0
    assert report["overlay_false_positive_count"] > 2
    assert report["overall_recommendation"] == NEXT_PRD_PATH_B
