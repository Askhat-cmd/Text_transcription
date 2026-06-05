from __future__ import annotations

from types import SimpleNamespace

from bot_agent.multiagent.final_answer_acceptance_gate import (
    FINAL_ANSWER_ACCEPTANCE_GATE_VERSION,
    build_final_answer_acceptance_gate_v1,
)


def _gate(
    *,
    user_message: str,
    final_answer: str,
    act: str = "direct_question",
    obligation: str = "answer_direct_question",
    unanswered: dict | None = None,
    previous: str = "",
    writer_debug: dict | None = None,
) -> dict:
    return build_final_answer_acceptance_gate_v1(
        user_message=user_message,
        final_answer=final_answer,
        dialogue_act_resolution={"dialogue_act": act},
        answer_obligation_resolution={"answer_obligation": obligation},
        unanswered_question_state_before=unanswered or {
            "answer_required": act.endswith("question"),
            "last_direct_user_question": user_message,
            "answer_status": "pending",
        },
        last_assistant_offer_before={},
        dialogue_style_state={},
        final_answer_directive={"must_answer": user_message},
        writer_debug=writer_debug or {},
        validator_result=SimpleNamespace(is_blocked=False),
        previous_assistant_message=previous,
    )


def test_gate_blocks_prd_hf1_stale_stub_phrase() -> None:
    payload = _gate(
        user_message="Я потерял работу и чувствую себя невостребованным. Как распутать этот узел?",
        final_answer=(
            "Сейчас полезнее прямое объяснение механизма: автоматический контроль может перегружать "
            "внимание еще до действия."
        ),
        act="concrete_situation_question",
        obligation="answer_concrete_situation",
    )

    assert payload["version"] == FINAL_ANSWER_ACCEPTANCE_GATE_VERSION
    assert payload["status"] == "failed"
    assert payload["must_quarantine_answer"] is True
    assert "stale_stub_detected" in payload["failed_checks"]
    assert payload["can_mark_question_answered"] is False
    assert payload["can_save_as_healthy_context"] is False


def test_gate_accepts_concrete_answer_with_user_anchors() -> None:
    payload = _gate(
        user_message=(
            "Мне 50, в семье напряжение, на работе сокращение, я в ступоре и чувствую "
            "невостребованность. Как распутать узел убеждений?"
        ),
        final_answer=(
            "Здесь узел держится сразу в нескольких местах: возраст 50 звучит как приговор, "
            "семья добавляет давление, а сокращение на работе усиливает чувство невостребованности. "
            "Распутывать это лучше не через один совет, а через отделение фактов от убеждений: факт - "
            "работа изменилась, убеждение - будто ты стал бесполезным. Когда эти слои разделены, "
            "появляется место для следующего решения."
        ),
        act="concrete_situation_question",
        obligation="answer_concrete_situation",
    )

    assert payload["status"] == "passed"
    assert payload["answer_considered_real"] is True
    assert len(payload["quality_signals"]["concrete_anchor_hits"]) >= 3


def test_gate_blocks_greeting_mechanism_lecture() -> None:
    payload = _gate(
        user_message="Привет, дорогой бот",
        final_answer="Ключевой механизм в том, что автоматический контроль заранее забирает ресурс.",
        act="greeting",
        obligation="continue_thread",
        unanswered={"answer_required": False, "answer_status": "answered"},
    )

    assert payload["status"] == "failed"
    assert "greeting_answered_with_mechanism_explanation" in payload["failed_checks"]


def test_gate_blocks_markdown_request_without_markdown() -> None:
    payload = _gate(
        user_message="Ответь markdown: жирный заголовок и список из трех пунктов",
        final_answer="Заголовок. Первый пункт. Второй пункт. Третий пункт.",
        act="direct_question",
        obligation="answer_direct_question",
    )

    assert payload["status"] == "failed"
    assert "markdown_requested_but_plain_text_only" in payload["failed_checks"]


def test_gate_detects_repeated_bad_answer() -> None:
    previous = "Сфокусируюсь на разборе, без практик по умолчанию."
    payload = _gate(
        user_message="ты снова не ответил мне на вопрос",
        final_answer=previous,
        act="repair_complaint",
        obligation="repair_and_answer_last_question",
        unanswered={
            "answer_required": True,
            "last_direct_user_question": "что такое нейросталкинг?",
            "answer_status": "pending",
        },
        previous=previous,
    )

    assert payload["status"] == "failed"
    assert "answer_repeats_previous_bad_answer" in payload["failed_checks"]
    assert "repair_failed_to_answer_recovered_question" in payload["failed_checks"]
