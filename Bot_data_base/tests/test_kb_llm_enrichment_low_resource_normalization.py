from __future__ import annotations

from tools.kb_llm_enrichment import _ensure_low_resource_avoid_when, _select_report_recommendation


def test_low_resource_avoid_when_autofilled_when_missing() -> None:
    avoid_when, autofilled = _ensure_low_resource_avoid_when(
        avoid_when=["когда практика не подходит"],
        safety_flags=["not_for_direct_quote", "practice_requires_low_resource_check"],
    )
    assert autofilled is True
    assert any("низком ресурсе" in item for item in avoid_when)


def test_low_resource_avoid_when_not_autofilled_when_present() -> None:
    avoid_when, autofilled = _ensure_low_resource_avoid_when(
        avoid_when=["когда у пользователя мало сил, кризис или выраженная перегрузка"],
        safety_flags=["practice_requires_low_resource_check"],
    )
    assert autofilled is False
    assert len(avoid_when) == 1


def test_hf3_recommendation_switches_to_hf4_on_failed_gate() -> None:
    recommendation = _select_report_recommendation(
        run_tag="PRD-046.0.5-RUN1-HF3",
        real_llm_run=True,
        validation_failed_ratio=0.2,
        unknown_lens_candidates=0,
        production_candidate_ready=False,
        promotion_allowed=False,
    )
    assert recommendation.startswith("PRD-046.0.5-RUN1-HF4")


def test_hf3_recommendation_switches_to_turn_summary_on_passed_gate() -> None:
    recommendation = _select_report_recommendation(
        run_tag="PRD-046.0.5-RUN1-HF3",
        real_llm_run=True,
        validation_failed_ratio=0.0,
        unknown_lens_candidates=0,
        production_candidate_ready=True,
        promotion_allowed=False,
    )
    assert recommendation.startswith("PRD-045.6.3")
