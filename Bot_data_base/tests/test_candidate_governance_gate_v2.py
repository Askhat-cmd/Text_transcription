from __future__ import annotations

from tools.clean_source_reprocess import build_candidate_governance_gate


def _base_stats() -> dict:
    return {
        "candidate_blocks_count": 10,
        "source_id_consistency_rate": 1.0,
        "governance_present_rate": 1.0,
        "chunking_quality_present_rate": 1.0,
        "allowed_use_present_rate": 1.0,
        "safety_flags_present_rate": 1.0,
        "sd_labeling_active": False,
    }


def test_gate_v2_passed_when_no_blockers_and_no_calibration_risks() -> None:
    gate = build_candidate_governance_gate(
        source_prd="PRD-046.0.8-HF1",
        preflight={"passed": True},
        candidate_stats=_base_stats(),
        practice_like_report={"practice_like_misclassified_count": 0},
        no_mutation_check={"passed": True},
        candidate_blocks=[],
        practice_taxonomy_report={
            "direct_practice_misclassified_count": 0,
            "unsafe_practice_suggestion_count": 0,
            "contextual_false_positive_count": 0,
        },
    )
    assert gate["schema_version"] == "candidate_governance_gate_v2"
    assert gate["status"] == "passed"


def test_gate_v2_candidate_needs_calibration_on_contextual_warnings() -> None:
    gate = build_candidate_governance_gate(
        source_prd="PRD-046.0.8-HF1",
        preflight={"passed": True},
        candidate_stats=_base_stats(),
        practice_like_report={"practice_like_misclassified_count": 0},
        no_mutation_check={"passed": True},
        candidate_blocks=[],
        practice_taxonomy_report={
            "direct_practice_misclassified_count": 0,
            "unsafe_practice_suggestion_count": 0,
            "contextual_false_positive_count": 2,
        },
    )
    assert gate["status"] == "candidate_needs_governance_calibration"
    assert "contextual_false_positive_detected" in gate["warnings"]


def test_gate_v2_failed_when_blockers_present() -> None:
    stats = _base_stats()
    stats["source_id_consistency_rate"] = 0.5
    gate = build_candidate_governance_gate(
        source_prd="PRD-046.0.8-HF1",
        preflight={"passed": True},
        candidate_stats=stats,
        practice_like_report={"practice_like_misclassified_count": 0},
        no_mutation_check={"passed": True},
        candidate_blocks=[],
        practice_taxonomy_report={
            "direct_practice_misclassified_count": 0,
            "unsafe_practice_suggestion_count": 0,
            "contextual_false_positive_count": 0,
        },
    )
    assert gate["status"] == "failed"
    assert "source_id_consistency_not_full" in gate["blockers"]
