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


def _base_taxonomy() -> dict:
    return {
        "direct_practice_misclassified_count": 0,
        "unsafe_practice_suggestion_count": 0,
        "contextual_false_positive_count": 0,
    }


def test_gate_v3_passed_when_candidate_ready_for_apply() -> None:
    gate = build_candidate_governance_gate(
        source_prd="PRD-046.0.8-HF2",
        preflight={"passed": True},
        candidate_stats=_base_stats(),
        practice_like_report={"practice_like_misclassified_count": 0},
        no_mutation_check={"passed": True},
        candidate_blocks=[],
        practice_taxonomy_report=_base_taxonomy(),
        mixed_intent_audit_report={
            "mixed_intent_alerts_before": 2,
            "mixed_intent_unresolved_count": 0,
            "mixed_intent_split_required_count": 0,
            "mixed_intent_review_only_count": 0,
            "mixed_intent_false_positive_count": 2,
        },
    )
    assert gate["schema_version"] == "candidate_governance_gate_v3"
    assert gate["status"] == "passed"
    assert gate["candidate_ready_for_apply"] is True


def test_gate_v3_manual_split_status_when_split_required_exists() -> None:
    gate = build_candidate_governance_gate(
        source_prd="PRD-046.0.8-HF2",
        preflight={"passed": True},
        candidate_stats=_base_stats(),
        practice_like_report={"practice_like_misclassified_count": 0},
        no_mutation_check={"passed": True},
        candidate_blocks=[],
        practice_taxonomy_report=_base_taxonomy(),
        mixed_intent_audit_report={
            "mixed_intent_alerts_before": 1,
            "mixed_intent_unresolved_count": 1,
            "mixed_intent_split_required_count": 1,
            "mixed_intent_review_only_count": 0,
            "mixed_intent_false_positive_count": 0,
        },
    )
    assert gate["status"] == "candidate_needs_manual_split_review"
    assert gate["candidate_ready_for_apply"] is False
