from __future__ import annotations

from pathlib import Path

from tools.kb_llm_enrichment import _build_overlay_readiness_report


def test_mock_overlay_never_production_ready() -> None:
    report = _build_overlay_readiness_report(
        overlay_path=Path("overlay.jsonl"),
        real_llm_run=False,
        validation_report={
            "chunks_enriched": 30,
            "validation_passed": 28,
            "validation_failed": 2,
            "unknown_lens_candidates": 0,
            "safety_governance_invariant_violations": 0,
            "raw_text_leak_check": "pass",
            "validation_reasons_distribution": {"summary_direct_quote_risk": 0},
        },
    )
    assert report["calibration_passed"] is True
    assert report["production_candidate_ready"] is False
    assert report["promotion_allowed"] is False
    assert "mock_run_not_production_eligible" in report["reasons"]


def test_real_overlay_production_ready_when_all_thresholds_pass() -> None:
    report = _build_overlay_readiness_report(
        overlay_path=Path("overlay.jsonl"),
        real_llm_run=True,
        validation_report={
            "chunks_enriched": 30,
            "validation_passed": 30,
            "validation_failed": 0,
            "hard_validation_failed": 0,
            "soft_review_warnings": 2,
            "unknown_lens_candidates": 0,
            "safety_governance_invariant_violations": 0,
            "raw_text_leak_check": "pass",
            "validation_reasons_distribution": {"summary_direct_quote_risk": 0},
        },
        allow_promotion_candidate=False,
    )
    assert report["calibration_passed"] is True
    assert report["production_candidate_ready"] is True
    assert report["promotion_allowed"] is False
    assert "manual_promotion_not_requested" in report["promotion_reasons"]
    assert report["reasons"] == []


def test_real_overlay_not_ready_with_high_failed_ratio() -> None:
    report = _build_overlay_readiness_report(
        overlay_path=Path("overlay.jsonl"),
        real_llm_run=True,
        validation_report={
            "chunks_enriched": 20,
            "validation_passed": 10,
            "validation_failed": 10,
            "hard_validation_failed": 10,
            "unknown_lens_candidates": 0,
            "safety_governance_invariant_violations": 0,
            "raw_text_leak_check": "pass",
            "validation_reasons_distribution": {},
        },
        allow_promotion_candidate=False,
    )
    assert report["production_candidate_ready"] is False
    assert "validation_failed_ratio_above_threshold" in report["reasons"]
