from __future__ import annotations

from bot_agent.multiagent.dialogue_pragmatics import build_dialogue_pragmatics_v1


def test_yes_after_phrase_offer_is_contextual_followup() -> None:
    payload = build_dialogue_pragmatics_v1(
        user_message="да",
        conversation_context="Assistant: Хочешь, я предложу одну короткую фразу для внутренней пометки?",
        previous_assistant_message="Хочешь, я предложу одну короткую фразу для внутренней пометки?",
        dialogue_policy={"active_concept": "нейросталкинг"},
    )
    assert payload["is_short_utterance"] is True
    assert payload["is_contextual_followup"] is True
    assert payload["previous_assistant_offer_type"] == "short_phrase"
    assert payload["should_answer_directly"] is True
    assert payload["should_not_ask_confirmation_again"] is True


def test_da_konechno_after_example_offer_keeps_context() -> None:
    payload = build_dialogue_pragmatics_v1(
        user_message="да конечно",
        conversation_context="Assistant: Хочешь, объясню это на примере?",
        previous_assistant_message="Хочешь, объясню это на примере?",
        dialogue_policy={"active_concept": "нейросталкинг"},
    )
    assert payload["is_contextual_followup"] is True
    assert payload["previous_assistant_offer_type"] == "example"
    assert payload["retrieval_need_hint"] in {"example_or_concept_grounding", "contextual_optional"}


def test_short_yes_without_context_is_not_crash_contextual_false() -> None:
    payload = build_dialogue_pragmatics_v1(
        user_message="да",
        conversation_context="",
        previous_assistant_message="",
        dialogue_policy={},
    )
    assert payload["is_short_utterance"] is True
    assert payload["is_contextual_followup"] is False
    assert payload["reason"] in {"short_utterance_without_context", "none"}


def test_dissatisfaction_is_repair_signal() -> None:
    payload = build_dialogue_pragmatics_v1(
        user_message="ты снова не ответил на свой же вопрос, да предложи",
        conversation_context="Assistant: Хочешь, я предложу короткую фразу?",
        previous_assistant_message="Хочешь, я предложу короткую фразу?",
        dialogue_policy={},
    )
    assert payload["repair_user_dissatisfaction"] is True
    assert payload["should_answer_directly"] is True
    assert payload["should_not_ask_confirmation_again"] is True


def test_greeting_repair_complaint_is_repair_signal() -> None:
    payload = build_dialogue_pragmatics_v1(
        user_message="почему ты начал объяснять механизм, я просто поздоровался?",
        conversation_context="Assistant: Привет, рад знакомству. Как ты сейчас себя чувствуешь?",
        previous_assistant_message="Привет, рад знакомству. Как ты сейчас себя чувствуешь?",
        dialogue_policy={},
    )
    assert payload["short_utterance_type"] == "repair_feedback"
    assert payload["repair_user_dissatisfaction"] is True
    assert payload["followup_relation"] == "repair_after_failed_answer"
    assert payload["should_answer_directly"] is True
