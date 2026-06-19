from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bot_agent.multiagent.answer_obligation_resolver import build_answer_obligation_resolver_v1
from bot_agent.multiagent.dialogue_act_resolver import build_dialogue_act_resolution_v1
from bot_agent.multiagent.dialogue_style_state import build_dialogue_style_state_v1
from bot_agent.multiagent.final_answer_directive import build_final_answer_directive_v1
from bot_agent.multiagent.unanswered_question_tracker import build_unanswered_question_state_v1


@pytest.mark.parametrize(
    ("message", "expected_act"),
    [
        ("Я разговариваю на работе с коллегой и вижу что он врет.", "concrete_situation_question"),
        ("Это снова ответ бота, а не живой разговор.", "meta_system_feedback"),
        ("Этот бот опять уходит в лекцию.", "meta_system_feedback"),
    ],
)
def test_meta_feedback_uses_word_boundaries_instead_of_substrings(message: str, expected_act: str) -> None:
    payload = build_dialogue_act_resolution_v1(
        user_message=message,
        dialogue_pragmatics={},
        last_assistant_offer={},
        knowledge_answer_guard={},
    )
    assert payload["dialogue_act"] == expected_act


@pytest.mark.parametrize(
    "message",
    [
        "Я работаю и все время жду удара.",
        "Я разработчик, но на работе зажимаюсь и молчу.",
        "На работе я все время жду подвоха.",
    ],
)
def test_work_words_do_not_trigger_meta_feedback(message: str) -> None:
    payload = build_dialogue_act_resolution_v1(
        user_message=message,
        dialogue_pragmatics={},
        last_assistant_offer={},
        knowledge_answer_guard={},
    )
    assert payload["dialogue_act"] != "meta_system_feedback"


def test_explicit_no_practice_cause_request_routes_to_current_turn_answer() -> None:
    user_message = "мне не нужна практика, я просто хочу понять как быть с самой причиной гнева а не с ее последствиями!"
    act = build_dialogue_act_resolution_v1(
        user_message=user_message,
        dialogue_pragmatics={},
        last_assistant_offer={"is_open": True, "offer_type": "explain_examples"},
        knowledge_answer_guard={},
    )
    assert act["dialogue_act"] == "concrete_situation_question"

    unanswered = build_unanswered_question_state_v1(
        previous_state={
            "last_direct_user_question": "а что делать с гневом, меня распирает от ненависти когда я вижу как кто то врет!",
            "turn_index": 4,
            "answer_required": True,
            "answer_status": "pending_quarantined_answer",
            "reason": "direct_question",
        },
        user_message=user_message,
        dialogue_act_resolution=act,
        turn_index=5,
    )
    assert unanswered["last_direct_user_question"] == user_message
    assert unanswered["answer_required"] is True

    style = build_dialogue_style_state_v1(
        previous_state={},
        user_message=user_message,
        dialogue_act_resolution=act,
    )
    obligation = build_answer_obligation_resolver_v1(
        dialogue_act_resolution=act,
        last_assistant_offer={"is_open": True, "offer_type": "explain_examples"},
        unanswered_question_state=unanswered,
        dialogue_style_state=style,
        dialogue_policy={"profile": "mvp_free_dialogue", "profile_preset": "free_dialogue_default"},
    )
    assert obligation["answer_obligation"] == "answer_concrete_situation"
    assert obligation["answer_shape"] == "contextual_explanation"
    assert obligation["question_policy"] == "optional_none"

    directive = build_final_answer_directive_v1(
        user_message=user_message,
        dialogue_policy={
            "profile": "mvp_free_dialogue",
            "profile_preset": "free_dialogue_default",
            "dialogue_act_resolution": act,
            "dialogue_style_state": style,
            "last_assistant_offer": {"is_open": True, "offer_type": "explain_examples"},
            "unanswered_question_state": unanswered,
            "soft_guidance": [],
        },
        dialogue_pragmatics={},
        response_planner={"answer_shape": "structured_explanation", "question_policy": "optional_none"},
        active_line={},
        diagnostic_card={},
        diagnostic_center_shadow={},
        retrieval_decision={},
        knowledge_answer_guard={},
        thread_state=SimpleNamespace(safety_active=False),
        state_snapshot=SimpleNamespace(safety_flag=False),
        answer_obligation_resolution=obligation,
        unified_dialogue_profile={"version": "unified_dialogue_policy_v2", "soft_guidance": []},
    ).to_dict()

    assert directive["must_answer"] == user_message
    assert directive["answer_obligation"] == "answer_concrete_situation"


def test_long_concrete_turn_with_not_wanting_public_conflict_is_not_offer_rejection() -> None:
    message = (
        "Давай на примере. Я разговариваю на работе с коллегой и вижу что он врет, "
        "но по должности он выше, и я не хочу его при всех уличать во лжи"
    )
    payload = build_dialogue_act_resolution_v1(
        user_message=message,
        dialogue_pragmatics={"is_contextual_followup": False},
        last_assistant_offer={"is_open": True, "offer_type": "example"},
        knowledge_answer_guard={},
    )
    assert payload["dialogue_act"] == "concrete_situation_question"
