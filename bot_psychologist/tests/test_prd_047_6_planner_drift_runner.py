from __future__ import annotations

import json
from pathlib import Path

from scripts.run_prd_047_6_planner_drift_guard_cases import (
    DEFAULT_DATASET,
    _build_negative_regression,
    _extract_live_drift_payload,
    _evaluate_direct_case,
    _validate_dataset,
)


def test_dataset_has_required_coverage() -> None:
    cases = json.loads(Path(DEFAULT_DATASET).read_text(encoding="utf-8-sig"))
    ok, errors, coverage = _validate_dataset(cases)
    assert ok is True
    assert errors == []
    assert coverage["safety_grounding_positive"] >= 4
    assert coverage["short_support_positive"] >= 4


def test_direct_case_fails_on_missing_required_flag() -> None:
    case = {
        "case_id": "direct_fail",
        "group": "question_policy_none",
        "turns": [{"role": "user", "content": "q"}],
        "planner": {
            "next_move": "deepen_mechanism",
            "answer_shape": "mechanism_explanation",
            "question_policy": "none",
            "practice_policy": "forbidden",
            "revoicing_policy": "suppressed",
        },
        "candidate_answer": "Почему так происходит?",
        "expected_drift": {"status": "ok", "must_have_flags": []},
    }
    result = _evaluate_direct_case(case)
    assert result["evaluation"]["passed"] is False
    assert "status_match" in result["evaluation"]["failure_reasons"]


def test_extract_live_drift_payload_missing_payload_fails() -> None:
    drift, reason = _extract_live_drift_payload({"debug": {}, "trace": {}})
    assert drift is None
    assert reason == "missing_live_api_debug_planner_drift_guard"


def test_extract_live_drift_payload_fallback_is_rejected() -> None:
    drift, reason = _extract_live_drift_payload(
        {
            "debug": {
                "planner_drift_guard": {
                    "version": "planner_drift_guard_v1",
                    "enabled": True,
                    "status": "warning",
                    "flags": ["drift_guard_exception"],
                }
            }
        }
    )
    assert isinstance(drift, dict)
    assert reason == "live_planner_drift_guard_exception_fallback"


def test_negative_regression_fixture_detects_bad_classes() -> None:
    payload = _build_negative_regression()
    assert payload["expected_passed"] is False
    assert payload["actual_passed"] is True
