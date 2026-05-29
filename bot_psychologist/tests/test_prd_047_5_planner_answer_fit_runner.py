from __future__ import annotations

import json
from pathlib import Path

from scripts.run_prd_047_5_planner_answer_fit_cases import (
    DEFAULT_DATASET,
    _build_false_positive_regression,
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


def test_answer_fit_fails_safety_planner_with_mechanism_answer() -> None:
    checks, reasons = _evaluate_answer_fit(
        "Здесь важнее увидеть механизм: прогнозирование и контроль забирают ресурс до начала действия.",
        {"max_chars": 320, "max_questions": 0, "forbidden_markers": ["теория", "лекция"]},
        {
            "next_move": "stabilize_safety",
            "answer_shape": "safety_grounding",
            "question_policy": "none",
            "practice_policy": "required_for_safety_or_grounding",
        },
    )
    assert checks["safety_no_mechanism_language"] is False
    assert checks["planner_answer_shape_alignment"] is False
    assert "safety_no_mechanism_language" in reasons


def test_answer_fit_fails_short_support_with_analysis_answer() -> None:
    checks, reasons = _evaluate_answer_fit(
        "Похоже, здесь включается программа через контроль и паттерн.",
        {"max_chars": 260, "max_questions": 0, "forbidden_markers": []},
        {
            "next_move": "give_short_support",
            "answer_shape": "short_support",
            "question_policy": "none",
            "practice_policy": "forbidden",
        },
    )
    assert checks["short_support_not_lecture"] is False
    assert checks["planner_answer_shape_alignment"] is False
    assert "short_support_not_lecture" in reasons


def test_answer_fit_fails_question_policy_none_with_question() -> None:
    checks, reasons = _evaluate_answer_fit(
        "Я рядом. Что сейчас сильнее всего давит?",
        {"max_chars": 260, "max_questions": 1, "forbidden_markers": []},
        {
            "next_move": "give_short_support",
            "answer_shape": "short_support",
            "question_policy": "none",
            "practice_policy": "forbidden",
        },
    )
    assert checks["question_policy_none_strict"] is False
    assert "question_policy_none_strict" in reasons


def test_answer_fit_fails_practice_forbidden_with_step() -> None:
    checks, reasons = _evaluate_answer_fit(
        "Сделай один шаг: поставь таймер и выпиши мысль.",
        {"max_chars": 420, "max_questions": 0, "forbidden_markers": []},
        {
            "next_move": "deepen_mechanism",
            "answer_shape": "mechanism_explanation",
            "question_policy": "none",
            "practice_policy": "forbidden",
        },
    )
    assert checks["practice_policy_forbidden_strict"] is False
    assert "practice_policy_forbidden_strict" in reasons


def test_answer_fit_passes_valid_safety_grounding_short_answer() -> None:
    checks, reasons = _evaluate_answer_fit(
        "Я рядом. Сейчас важнее короткая опора здесь-и-сейчас, без перегруза.",
        {"max_chars": 320, "max_questions": 0, "forbidden_markers": ["теория", "лекция"]},
        {
            "next_move": "stabilize_safety",
            "answer_shape": "safety_grounding",
            "question_policy": "none",
            "practice_policy": "required_for_safety_or_grounding",
        },
    )
    assert checks["safety_no_mechanism_language"] is True
    assert checks["planner_answer_shape_alignment"] is True
    assert reasons == []


def test_answer_fit_passes_valid_short_support_answer() -> None:
    checks, reasons = _evaluate_answer_fit(
        "Я рядом. Сейчас не нужно ничего разбирать. Можно просто немного снизить внутреннее давление.",
        {"max_chars": 260, "max_questions": 0, "forbidden_markers": ["практик", "упражн", "таймер"]},
        {
            "next_move": "give_short_support",
            "answer_shape": "short_support",
            "question_policy": "none",
            "practice_policy": "forbidden",
        },
    )
    assert checks["short_support_not_lecture"] is True
    assert checks["short_support_supportive_contact"] is True
    assert checks["planner_answer_shape_alignment"] is True
    assert reasons == []


def test_live_runner_requires_api_planner_no_fallback() -> None:
    planner, reason = _extract_planner_from_payload(
        {"debug": {"response_planner": {"enabled": True, "_fallback_source": "local_builder"}}}
    )
    assert isinstance(planner, dict)
    assert reason == "live_response_planner_fallback_not_allowed_for_acceptance"


def test_dataset_contains_regression_for_pq_007_or_equivalent() -> None:
    items = json.loads(Path(DEFAULT_DATASET).read_text(encoding="utf-8-sig"))
    assert isinstance(items, list)
    assert any(str(item.get("case_id")) == "pq_007_soft_distress_cant" for item in items if isinstance(item, dict))


def test_false_positive_regression_fixture_is_failed() -> None:
    artifact = _build_false_positive_regression()
    assert artifact["expected_passed"] is False
    assert artifact["actual_passed"] is False


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
