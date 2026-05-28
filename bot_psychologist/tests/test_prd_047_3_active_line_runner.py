from __future__ import annotations

from scripts.run_prd_047_3_active_line_cases import _evaluate_case


def _case(query: str, expected: dict, *, turn_index: int = 1) -> dict:
    return {
        "id": "case",
        "group": "T",
        "thread_id": "thread",
        "turn_index": turn_index,
        "query": query,
        "expected": expected,
    }


def _trace(
    *,
    user_intent: str,
    continuity_mode: str,
    should_offer_practice: bool = False,
    repair_mode: str | None = None,
) -> dict:
    return {
        "version": "active_line_v1",
        "active_line": "смысловая линия",
        "user_intent": user_intent,
        "continuity_mode": continuity_mode,
        "next_meaningful_move": "следующий смысловой ход",
        "should_continue_line": continuity_mode in {"continue_existing_line", "repair_and_continue_line"},
        "should_ask_question": False,
        "should_offer_practice": should_offer_practice,
        "revoicing_allowed": False,
        "revoicing_style": "suppressed",
        "repair_mode": repair_mode,
        "evidence_turn_ids": [],
        "confidence": 0.8,
        "practice_suppression_active": not should_offer_practice,
    }


def test_mechanical_revoicing_opener_fails_continuity_case() -> None:
    case = _case(
        "прояснение по рабочей задаче",
        {"continuity_mode": "continue_existing_line", "user_intent": "understand_mechanism", "no_practice": True},
        turn_index=2,
    )
    answer = "Асхат, похоже, вы хотите понять, что происходит и как с этим быть."
    result = _evaluate_case(
        case=case,
        answer=answer,
        active_line_trace=_trace(user_intent="understand_mechanism", continuity_mode="continue_existing_line"),
    )
    assert result["passed"] is False
    assert result["checks"]["no_mechanical_revoicing"] is False


def test_breathing_or_timer_fails_understand_mechanism_case() -> None:
    case = _case(
        "хочу понять механизм",
        {"user_intent": "understand_mechanism", "continuity_mode": "start_new_line", "no_practice": True},
    )
    answer = "Поставь таймер на 5 минут и сделай медленный вдох."
    result = _evaluate_case(
        case=case,
        answer=answer,
        active_line_trace=_trace(user_intent="understand_mechanism", continuity_mode="start_new_line"),
    )
    assert result["passed"] is False
    assert result["checks"]["no_unsolicited_practice"] is False


def test_correction_with_new_practice_fails() -> None:
    case = _case(
        "почему ты предлагаешь практику",
        {
            "user_intent": "correction_of_bot",
            "continuity_mode": "repair_and_continue_line",
            "repair_required": True,
            "no_practice": True,
            "no_new_practice_after_correction": True,
        },
        turn_index=3,
    )
    answer = "Сделайте шаг: поставьте таймер на 5 минут и начните действие."
    result = _evaluate_case(
        case=case,
        answer=answer,
        active_line_trace=_trace(
            user_intent="correction_of_bot",
            continuity_mode="repair_and_continue_line",
            repair_mode="acknowledge_and_return_to_mechanism",
        ),
    )
    assert result["checks"]["no_new_practice_after_practice_complaint"] is False


def test_thanks_with_extra_step_offer_fails() -> None:
    case = _case(
        "спасибо",
        {"user_intent": "thanks_close", "continuity_mode": "close_gently", "no_practice": True, "no_step_offer": True},
    )
    answer = "Пожалуйста. Предложу еще один шаг, если хочешь."
    result = _evaluate_case(
        case=case,
        answer=answer,
        active_line_trace=_trace(user_intent="thanks_close", continuity_mode="close_gently"),
    )
    assert result["passed"] is False
    assert result["checks"]["no_step_offer_on_close"] is False


def test_explicit_practice_request_passes_with_one_step() -> None:
    case = _case(
        "дай один шаг",
        {"user_intent": "ask_for_direct_step", "continuity_mode": "start_new_line", "practice_allowed": True},
    )
    answer = "Один шаг: открой задачу и за 5 минут сформулируй первый проверяемый результат."
    result = _evaluate_case(
        case=case,
        answer=answer,
        active_line_trace=_trace(
            user_intent="ask_for_direct_step",
            continuity_mode="start_new_line",
            should_offer_practice=True,
        ),
    )
    assert result["passed"] is True
    assert result["checks"]["practice_allowed_when_explicit"] is True
