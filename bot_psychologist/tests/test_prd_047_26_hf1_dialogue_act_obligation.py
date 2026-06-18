from __future__ import annotations

from bot_agent.multiagent.answer_obligation_resolver import build_answer_obligation_resolver_v1
from bot_agent.multiagent.dialogue_act_resolver import build_dialogue_act_resolution_v1


def _resolve(user_message: str) -> tuple[dict, dict]:
    act = build_dialogue_act_resolution_v1(
        user_message=user_message,
        dialogue_pragmatics={},
        last_assistant_offer={},
        knowledge_answer_guard={},
    )
    obligation = build_answer_obligation_resolver_v1(
        dialogue_act_resolution=act,
        last_assistant_offer={},
        unanswered_question_state={},
        dialogue_style_state={},
        dialogue_policy={"profile": "mvp_free_dialogue", "profile_preset": "free_dialogue_default"},
    )
    return act, obligation


def test_five_drivers_routes_to_knowledge_answer() -> None:
    act, obligation = _resolve("Расскажи о пяти драйверах выживания.")

    assert act["dialogue_act"] == "knowledge_question"
    assert act["reason"] == "explicit_answer_first_knowledge_request"
    assert act["source"] == "explicit_direct_question_override"
    assert obligation["answer_obligation"] == "answer_knowledge_question"
    assert obligation["reason"] == "knowledge_question_requires_direct_answer"


def test_control_as_safety_short_request_stays_answer_first() -> None:
    act, obligation = _resolve("Объясни коротко, что значит «контроль как безопасность», без встречного вопроса.")

    assert act["dialogue_act"] == "knowledge_question"
    assert "no_counter_question_requested" in act["evidence"]
    assert obligation["answer_obligation"] in {
        "answer_knowledge_question",
        "acknowledge_style_preference_then_answer",
    }
    assert obligation["question_policy"] == "optional_none"


def test_bounded_practice_request_gets_explicit_practice_obligation() -> None:
    act, obligation = _resolve("Дай одну короткую практику, чтобы заметить драйвер «Будь сильным».")

    assert act["dialogue_act"] == "practice_request"
    assert act["reason"] == "explicit_bounded_practice_request"
    assert obligation["answer_obligation"] == "provide_one_bounded_practice"
    assert obligation["answer_shape"] == "one_short_practice"
    assert obligation["question_policy"] == "none"
    assert obligation["practice_policy"] == "allowed_explicit_request"


def test_panic_control_support_question_does_not_fall_back_to_continue_thread() -> None:
    act, obligation = _resolve("Когда накрывает паникой, почему контроль становится сильнее?")

    assert act["dialogue_act"] in {
        "concrete_situation_question",
        "direct_question",
        "knowledge_question",
    }
    assert obligation["answer_obligation"] in {
        "answer_concrete_situation",
        "answer_direct_question",
        "answer_knowledge_question",
    }
    assert obligation["answer_obligation"] != "continue_thread"
