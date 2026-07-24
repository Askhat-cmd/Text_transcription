from __future__ import annotations

from bot_agent.multiagent.dialogue_pragmatics import build_dialogue_pragmatics_v1


def test_affirmation_with_intent_is_contextual_followup() -> None:
    payload = build_dialogue_pragmatics_v1(
        user_message="Да, конечно, дай пример!",
        conversation_context="Assistant: Хочешь, объясню это на примере?",
        previous_assistant_message="Хочешь, объясню это на примере?",
        dialogue_policy={"active_concept": "нейросталкинг"},
    )
    assert payload["is_contextual_followup"] is True
    assert payload["previous_assistant_offer_type"] == "example"
    assert payload["should_not_ask_confirmation_again"] is True


def test_thanks_is_close_ack_not_contextual_followup() -> None:
    payload = build_dialogue_pragmatics_v1(
        user_message="спасибо",
        conversation_context="Assistant: Рад, что помогло.",
        previous_assistant_message="Рад, что помогло.",
        dialogue_policy={},
    )
    assert payload["short_utterance_type"] == "close_ack"
    assert payload["is_contextual_followup"] is False
    assert payload["retrieval_need_hint"] == "none"


def test_thanks_with_extra_words_is_close_ack() -> None:
    payload = build_dialogue_pragmatics_v1(
        user_message="спасибо, этого достаточно",
        conversation_context="Assistant: Сделай один шаг прямо сейчас.",
        previous_assistant_message="Сделай один шаг прямо сейчас.",
        dialogue_policy={},
    )
    assert payload["short_utterance_type"] == "close_ack"
    assert payload["is_contextual_followup"] is False
    assert payload["followup_relation"] == "close_acknowledgement"
    assert payload["should_answer_directly"] is False


def test_thanks_with_intent_word_is_close_ack_not_followup() -> None:
    payload = build_dialogue_pragmatics_v1(
        user_message="понял, спасибо, буду разбираться",
        conversation_context="Assistant: Хочешь, объясню на примере?",
        previous_assistant_message="Хочешь, объясню на примере?",
        dialogue_policy={},
    )
    assert payload["short_utterance_type"] == "close_ack"
    assert payload["is_contextual_followup"] is False


def test_thanks_but_explain_more_is_still_imperative_followup() -> None:
    payload = build_dialogue_pragmatics_v1(
        user_message="спасибо, но объясни подробнее ещё раз",
        conversation_context="Assistant: Хочешь, объясню на примере?",
        previous_assistant_message="Хочешь, объясню на примере?",
        dialogue_policy={},
    )
    assert payload["short_utterance_type"] == "imperative_followup"
    assert payload["is_contextual_followup"] is True


def test_repair_request_short_followup_sets_repair_signal() -> None:
    payload = build_dialogue_pragmatics_v1(
        user_message="ответь на вопрос который я задавал ранее",
        conversation_context="Assistant: Хочешь, я предложу фразу?",
        previous_assistant_message="Хочешь, я предложу фразу?",
        dialogue_policy={},
    )
    assert payload["repair_user_dissatisfaction"] is True
    assert payload["should_answer_directly"] is True
