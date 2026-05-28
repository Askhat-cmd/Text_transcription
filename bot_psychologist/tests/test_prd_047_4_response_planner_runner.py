from __future__ import annotations

from scripts.run_prd_047_4_response_planner_cases import (
    _evaluate_case,
    _extract_live_actual_planner,
)


def _case(expected: dict) -> dict:
    return {
        "case_id": "rp_case",
        "group": "T",
        "expected": expected,
    }


def _planner(**kwargs) -> dict:
    base = {
        "version": "response_planner_v1",
        "enabled": True,
        "next_move": "deepen_mechanism",
        "answer_shape": "mechanism_explanation",
        "practice_policy": "forbidden",
        "question_policy": "none",
        "revoicing_policy": "suppressed",
        "must_avoid": ["не предлагать практику"],
    }
    base.update(kwargs)
    return base


def test_runner_evaluate_case_detects_policy_mismatch_in_dry() -> None:
    case = _case(
        {
            "next_move": "deepen_mechanism",
            "answer_shape": "mechanism_explanation",
            "practice_policy": "forbidden",
            "question_policy": "none",
            "revoicing_policy": "suppressed",
            "required_must_avoid_contains": ["не предлагать практику"],
        }
    )
    result = _evaluate_case(
        case=case,
        actual=_planner(practice_policy="one_micro_step_allowed"),
        expected_local=None,
        mode="dry",
    )
    assert result["passed"] is False
    assert result["checks"]["practice_policy_match"] is False


def test_runner_fails_live_when_actual_planner_missing() -> None:
    actual, reason = _extract_live_actual_planner({"debug": {}, "trace": {}})
    assert actual is None
    assert reason == "missing_live_api_debug_response_planner"


def test_runner_fails_live_on_fallback_marker() -> None:
    payload = {
        "debug": {
            "response_planner": _planner(**{"_fallback_source": "local_builder"}),
        }
    }
    actual, reason = _extract_live_actual_planner(payload)
    assert isinstance(actual, dict)
    assert reason == "live_response_planner_fallback_not_allowed_for_acceptance"


def test_runner_fails_live_on_planner_error() -> None:
    payload = {
        "debug": {
            "response_planner": _planner(),
            "response_planner_error": "failed",
        }
    }
    actual, reason = _extract_live_actual_planner(payload)
    assert isinstance(actual, dict)
    assert reason == "live_response_planner_error_present"
