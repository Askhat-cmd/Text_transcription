from __future__ import annotations

from types import SimpleNamespace

from bot_agent.multiagent.final_answer_acceptance_gate import build_final_answer_acceptance_gate_v1
from bot_agent.multiagent.template_family_guard import (
    build_memory_contamination_guard_result,
    detect_template_family_leakage,
)


LEAKED_TEMPLATE = (
    "В твоем описании важно не свести все к одному общему механизму. "
    "1. Сначала отдели факты от вывода.\n"
    "2. Затем найди центральное убеждение.\n"
    "3. После этого проверь, что это убеждение заставляет делать.\n"
    "4. Практический смысл распутывания здесь в том, чтобы вернуть себе следующий ход."
)


def _gate(answer: str) -> dict:
    user = (
        "Мне 50 лет, семья, риск сокращения, ступор и чувство невостребованности. "
        "Как распутать этот клубок убеждений?"
    )
    return build_final_answer_acceptance_gate_v1(
        user_message=user,
        final_answer=answer,
        dialogue_act_resolution={"dialogue_act": "concrete_situation_question"},
        answer_obligation_resolution={"answer_obligation": "answer_concrete_situation"},
        unanswered_question_state_before={
            "answer_required": True,
            "last_direct_user_question": user,
            "answer_status": "pending",
        },
        last_assistant_offer_before={},
        dialogue_style_state={},
        final_answer_directive={"must_answer": user},
        writer_debug={},
        validator_result=SimpleNamespace(is_blocked=False),
        previous_assistant_message="",
    )


def test_template_family_guard_detects_exact_and_numbered_skeleton() -> None:
    payload = detect_template_family_leakage(LEAKED_TEMPLATE)

    assert payload["version"] == "template_family_guard_v1"
    assert payload["leak_detected"] is True
    assert "facts_vs_conclusion" in payload["markers"]
    assert "central_belief" in payload["markers"]
    assert payload["action"] == "retry_or_quarantine"
    assert payload["user_facing_replacement_created"] is False


def test_template_family_guard_allows_clean_answer() -> None:
    answer = (
        "Здесь важно удержать несколько живых опор: возраст 50 звучит как давление времени, "
        "семья добавляет ответственность, а риск сокращения усиливает ступор. Ответ не в том, "
        "чтобы объявить себя бесполезным, а в том, чтобы отделить рабочий факт от внутреннего "
        "приговора и выбрать ближайший разговор или решение, которое возвращает тебе действие."
    )

    payload = detect_template_family_leakage(answer)

    assert payload["leak_detected"] is False
    assert payload["markers"] == []
    assert payload["action"] == "passed"


def test_final_answer_gate_quarantines_template_family_leakage() -> None:
    gate = _gate(LEAKED_TEMPLATE)

    assert gate["status"] == "failed"
    assert "template_family_leakage_detected" in gate["failed_checks"]
    assert gate["template_family_guard"]["leak_detected"] is True
    assert gate["template_family_guard"]["user_facing_replacement_created"] is False
    assert gate["can_save_as_healthy_context"] is False
    assert gate["can_use_as_summary_source"] is False
    assert gate["can_save_last_assistant_offer"] is False
    assert gate["must_quarantine_answer"] is True


def test_memory_contamination_guard_blocks_healthy_memory_summary_and_offer() -> None:
    gate = _gate(LEAKED_TEMPLATE)
    decision = build_memory_contamination_guard_result(final_answer_acceptance_gate=gate)

    assert decision["contaminated"] is True
    assert decision["healthy_memory_allowed"] is False
    assert decision["summary_source_allowed"] is False
    assert decision["last_assistant_offer_allowed"] is False
    assert decision["template_family_guard"]["leak_detected"] is True
