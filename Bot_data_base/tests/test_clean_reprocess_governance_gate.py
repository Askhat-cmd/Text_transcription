from __future__ import annotations

from tools.clean_source_reprocess import build_candidate_governance_gate


def test_governance_gate_passed() -> None:
    gate = build_candidate_governance_gate(
        source_prd="PRD-046.0.8",
        preflight={"passed": True},
        candidate_stats={
            "candidate_blocks_count": 10,
            "source_id_consistency_rate": 1.0,
            "governance_present_rate": 1.0,
            "chunking_quality_present_rate": 1.0,
            "allowed_use_present_rate": 1.0,
            "safety_flags_present_rate": 1.0,
            "sd_labeling_active": False,
        },
        practice_like_report={"practice_like_misclassified_count": 0},
        no_mutation_check={"passed": True},
        candidate_blocks=[],
    )
    assert gate["status"] == "passed"


def test_governance_gate_needs_calibration() -> None:
    gate = build_candidate_governance_gate(
        source_prd="PRD-046.0.8",
        preflight={"passed": True},
        candidate_stats={
            "candidate_blocks_count": 10,
            "source_id_consistency_rate": 1.0,
            "governance_present_rate": 1.0,
            "chunking_quality_present_rate": 1.0,
            "allowed_use_present_rate": 1.0,
            "safety_flags_present_rate": 1.0,
            "sd_labeling_active": False,
        },
        practice_like_report={"practice_like_misclassified_count": 2},
        no_mutation_check={"passed": True},
        candidate_blocks=[],
    )
    assert gate["status"] == "candidate_needs_governance_calibration"


def test_governance_gate_failed_on_source_id_mismatch() -> None:
    gate = build_candidate_governance_gate(
        source_prd="PRD-046.0.8",
        preflight={"passed": True},
        candidate_stats={
            "candidate_blocks_count": 10,
            "source_id_consistency_rate": 0.9,
            "governance_present_rate": 1.0,
            "chunking_quality_present_rate": 1.0,
            "allowed_use_present_rate": 1.0,
            "safety_flags_present_rate": 1.0,
            "sd_labeling_active": False,
        },
        practice_like_report={"practice_like_misclassified_count": 0},
        no_mutation_check={"passed": True},
        candidate_blocks=[],
    )
    assert gate["status"] == "failed"
    assert "source_id_consistency_not_full" in gate["blockers"]
