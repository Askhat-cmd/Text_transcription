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
            "validation_reasons_distribution": {"summary_direct_quote_risk": 1},
        },
    )
    assert report["calibration_passed"] is True
    assert report["production_ready"] is False
    assert report["promotion_allowed"] is False
    assert "mock_run_not_production_eligible" in report["reasons"]


def test_real_overlay_production_ready_when_all_thresholds_pass() -> None:
    report = _build_overlay_readiness_report(
        overlay_path=Path("overlay.jsonl"),
        real_llm_run=True,
        validation_report={
            "chunks_enriched": 30,
            "validation_passed": 27,
            "validation_failed": 3,
            "unknown_lens_candidates": 0,
            "safety_governance_invariant_violations": 0,
            "raw_text_leak_check": "pass",
            "validation_reasons_distribution": {"summary_direct_quote_risk": 2},
        },
        hold_promotion=True,
    )
    assert report["calibration_passed"] is True
    assert report["production_ready"] is True
    assert report["promotion_allowed"] is False
    assert report["promotion_reason"] == "real_batch_ready_but_full_apply_requires_next_prd"
    assert report["reasons"] == []
