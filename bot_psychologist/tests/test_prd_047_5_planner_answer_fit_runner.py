from __future__ import annotations

from scripts.run_prd_047_5_planner_answer_fit_cases import (
    _evaluate_answer_fit,
    _extract_planner_from_payload,
    _validate_dataset,
)


def test_dataset_validation_fails_when_group_coverage_missing() -> None:
    cases = [
        {
            "case_id": "c1",
            "group": "low_resource_short_support",
            "thread_id": "t1",
            "turns": [{"role": "user", "content": "msg"}],
            "expected_planner": {
                "next_move": "give_short_support",
                "answer_shape": "short_support",
                "response_depth": "very_short",
                "question_policy": "none",
                "practice_policy": "forbidden",
                "revoicing_policy": "suppressed",
            },
            "expected_answer_fit": {"max_chars": 260, "max_questions": 0},
        }
    ]
    ok, errors, _coverage = _validate_dataset(cases)
    assert ok is False
    assert any("group_coverage_failed" in item for item in errors)


def test_answer_fit_detects_question_policy_violation() -> None:
    expected_fit = {
        "max_chars": 260,
        "max_questions": 0,
        "forbidden_markers": [],
    }
    expected_planner = {
        "next_move": "give_short_support",
        "answer_shape": "short_support",
    }
    checks, reasons = _evaluate_answer_fit(
        "one? two?",
        expected_fit,
        expected_planner,
    )
    assert checks["max_questions"] is False
    assert "max_questions" in reasons


def test_extract_live_planner_fails_on_missing_payload() -> None:
    planner, reason = _extract_planner_from_payload({"debug": {}, "trace": {}})
    assert planner is None
    assert reason == "missing_live_api_debug_response_planner"


def test_extract_live_planner_fails_on_fallback_marker() -> None:
    planner, reason = _extract_planner_from_payload(
        {"debug": {"response_planner": {"enabled": True, "_fallback_source": "local_builder"}}}
    )
    assert isinstance(planner, dict)
    assert reason == "live_response_planner_fallback_not_allowed_for_acceptance"
