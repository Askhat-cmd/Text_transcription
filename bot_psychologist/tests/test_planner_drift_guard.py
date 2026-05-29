from __future__ import annotations

from bot_agent.multiagent.planner_drift_guard import build_planner_drift_check


def _planner(**overrides):
    planner = {
        "next_move": "stabilize_safety",
        "answer_shape": "safety_grounding",
        "question_policy": "none",
        "practice_policy": "required_for_safety_or_grounding",
        "revoicing_policy": "suppressed",
    }
    planner.update(overrides)
    return planner


def test_safety_grounding_with_mechanism_is_critical() -> None:
    check = build_planner_drift_check(
        response_planner=_planner(),
        final_answer="Разберем механизм контроля и прогнозирования, он запускает цикл.",
    ).to_dict()
    assert check["status"] == "critical"
    assert "safety_mechanism_drift" in check["flags"]


def test_short_support_long_analysis_is_warning_or_critical() -> None:
    check = build_planner_drift_check(
        response_planner=_planner(
            next_move="give_short_support",
            answer_shape="short_support",
            practice_policy="forbidden",
        ),
        final_answer=(
            "Это длинный аналитический разбор механизма контроля и стратегии, "
            "который объясняет паттерн во множестве деталей и расширений."
        ),
    ).to_dict()
    assert check["status"] in {"warning", "critical"}
    assert any(flag in check["flags"] for flag in {"short_support_too_long", "short_support_missing_contact"})


def test_question_policy_none_with_question_sets_medium_flag() -> None:
    check = build_planner_drift_check(
        response_planner=_planner(next_move="deepen_mechanism", answer_shape="mechanism_explanation", practice_policy="forbidden"),
        final_answer="Почему ты снова идешь в этот цикл?",
    ).to_dict()
    assert check["status"] == "warning"
    assert "question_policy_violation" in check["flags"]


def test_practice_policy_forbidden_with_exercise_is_high() -> None:
    check = build_planner_drift_check(
        response_planner=_planner(next_move="deepen_mechanism", answer_shape="mechanism_explanation", practice_policy="forbidden"),
        final_answer="Сделай упражнение: поставь таймер и выпиши три мысли.",
    ).to_dict()
    assert check["status"] == "critical"
    assert "practice_policy_forbidden_violation" in check["flags"]


def test_valid_short_support_is_ok() -> None:
    check = build_planner_drift_check(
        response_planner=_planner(next_move="give_short_support", answer_shape="short_support", practice_policy="forbidden"),
        final_answer="Я рядом. Сейчас не нужно ничего доказывать, можно просто немного снизить напряжение.",
    ).to_dict()
    assert check["status"] == "ok"
    assert check["flags"] == []


def test_valid_safety_grounding_is_ok() -> None:
    check = build_planner_drift_check(
        response_planner=_planner(),
        final_answer="Я рядом. Сейчас важнее опора здесь и сейчас, чтобы мягко снизить перегруз.",
    ).to_dict()
    assert check["status"] == "ok"
    assert check["flags"] == []
