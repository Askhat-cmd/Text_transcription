from __future__ import annotations

from types import SimpleNamespace

from bot_agent.multiagent.concrete_answer_fit import evaluate_concrete_answer_fit
from bot_agent.multiagent.final_answer_acceptance_gate import build_final_answer_acceptance_gate_v1


def _gate(
    *,
    user_message: str,
    final_answer: str,
    act: str,
    obligation: str,
) -> dict:
    return build_final_answer_acceptance_gate_v1(
        user_message=user_message,
        final_answer=final_answer,
        dialogue_act_resolution={"dialogue_act": act},
        answer_obligation_resolution={"answer_obligation": obligation},
        unanswered_question_state_before={
            "answer_required": True,
            "last_direct_user_question": user_message,
            "answer_status": "pending",
        },
        last_assistant_offer_before={},
        dialogue_style_state={},
        final_answer_directive={"must_answer": user_message},
        writer_debug={},
        validator_result=SimpleNamespace(is_blocked=False),
        previous_assistant_message="",
    )


def test_generic_step_fails_explicit_one_practice_request() -> None:
    user_message = "Дай одну короткую практику, чтобы заметить драйвер «Будь сильным»."
    final_answer = "Сделай один шаг прямо сейчас: открой задачу и выполни первый минимальный фрагмент в течение 5 минут."

    gate = _gate(
        user_message=user_message,
        final_answer=final_answer,
        act="practice_request",
        obligation="provide_one_bounded_practice",
    )
    evaluator = evaluate_concrete_answer_fit(
        user_message=user_message,
        answer_text=final_answer,
        explicit_answer_need=True,
    )

    assert gate["status"] == "failed"
    assert "explicit_one_practice_request_not_fulfilled" in gate["failed_checks"]
    assert gate["can_save_as_healthy_context"] is False
    assert evaluator["practice_request_not_fulfilled"] is True
    assert evaluator["fit_status"] == "fail"


def test_textbook_panic_control_answer_fails_evaluator_and_gate() -> None:
    user_message = "Когда накрывает паникой, почему контроль становится сильнее?"
    final_answer = (
        "Потому что паника — это ощущение угрозы. 1. Включается симпатоадреналовая система. "
        "2. Префронтальная кора пытается вернуть порядок. 3. Автономная реакция тела усиливает контроль. "
        "4. Поэтому возникает замкнутый круг."
    )

    gate = _gate(
        user_message=user_message,
        final_answer=final_answer,
        act="concrete_situation_question",
        obligation="answer_concrete_situation",
    )
    evaluator = evaluate_concrete_answer_fit(
        user_message=user_message,
        answer_text=final_answer,
        explicit_answer_need=True,
    )

    assert gate["status"] == "failed"
    assert "support_direct_question_answer_too_textbook" in gate["failed_checks"]
    assert evaluator["support_answer_too_textbook"] is True
    assert evaluator["fit_status"] == "fail"


def test_good_short_practice_answer_passes() -> None:
    user_message = "Дай одну короткую практику, чтобы заметить драйвер «Будь сильным»."
    final_answer = (
        "Одна короткая практика: в момент, когда включается «Будь сильным», заметь место напряжения в теле "
        "и тихо назови про себя: «сейчас я снова держу всё через силу». Этого уже достаточно."
    )

    gate = _gate(
        user_message=user_message,
        final_answer=final_answer,
        act="practice_request",
        obligation="provide_one_bounded_practice",
    )
    evaluator = evaluate_concrete_answer_fit(
        user_message=user_message,
        answer_text=final_answer,
        explicit_answer_need=True,
    )

    assert gate["status"] == "passed"
    assert evaluator["practice_request_not_fulfilled"] is False
    assert evaluator["fit_status"] == "pass"


def test_good_supportive_panic_control_answer_passes() -> None:
    user_message = "Когда накрывает паникой, почему контроль становится сильнее?"
    final_answer = (
        "Потому что в момент паники телу кажется, что опора потеряна, и контроль становится попыткой быстро вернуть безопасность. "
        "Чем сильнее угроза ощущается в теле, тем сильнее хочется всё удержать головой, даже если это уже не помогает."
    )

    gate = _gate(
        user_message=user_message,
        final_answer=final_answer,
        act="concrete_situation_question",
        obligation="answer_concrete_situation",
    )
    evaluator = evaluate_concrete_answer_fit(
        user_message=user_message,
        answer_text=final_answer,
        explicit_answer_need=True,
    )

    assert gate["status"] == "passed"
    assert evaluator["support_answer_too_textbook"] is False
    assert evaluator["fit_status"] != "fail"


def test_greeting_regression_guard_still_holds() -> None:
    gate = _gate(
        user_message="Привет",
        final_answer="Ключевой механизм в том, что автоматический контроль заранее забирает ресурс.",
        act="greeting",
        obligation="continue_thread",
    )

    assert gate["status"] == "failed"
    assert "greeting_answered_with_mechanism_explanation" in gate["failed_checks"]
