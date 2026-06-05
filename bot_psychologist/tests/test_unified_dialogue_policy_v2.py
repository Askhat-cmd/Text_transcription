from __future__ import annotations

from bot_agent.multiagent.answer_obligation_resolver import build_answer_obligation_resolver_v1
from bot_agent.multiagent.dialogue_act_resolver import build_dialogue_act_resolution_v1
from bot_agent.multiagent.dialogue_policy import build_effective_dialogue_policy
from bot_agent.multiagent.last_assistant_offer_tracker import build_last_assistant_offer_v1
from bot_agent.multiagent.unanswered_question_tracker import build_unanswered_question_state_v1


_STATE = {"safety_flag": False}
_THREAD = {"safety_active": False, "response_mode": "reflect"}


def test_mvp_free_dialogue_alias_resolves_to_free_dialogue_default() -> None:
    payload = build_effective_dialogue_policy(
        profile="mvp_free_dialogue",
        user_message="объясни подробнее, что такое нейросталкинг?",
        state_snapshot=_STATE,
        thread_state=_THREAD,
        knowledge_answer_guard={"knowledge_answer": {"needed": True, "concept": "нейросталкинг"}},
    )
    assert payload["version"] == "unified_dialogue_policy_v2"
    assert payload["active_profile_alias"] == "mvp_free_dialogue"
    assert payload["profile_preset"] == "free_dialogue_default"


def test_safe_guided_is_preset_not_runtime_branch() -> None:
    payload = build_effective_dialogue_policy(
        profile="safe_guided",
        user_message="что такое нейросталкинг?",
        state_snapshot=_STATE,
        thread_state=_THREAD,
        knowledge_answer_guard={"knowledge_answer": {"needed": True, "concept": "нейросталкинг"}},
    )
    assert payload["version"] == "unified_dialogue_policy_v2"
    assert payload["profile_preset"] == "safe_guided"
    assert payload["diagnostic_center_role"] == "advisory_context_only"
    assert payload["planner_role"] == "advisory_context_only"


def test_diagnostic_center_advisory_only_boundary() -> None:
    payload = build_effective_dialogue_policy(
        profile="mvp_free_dialogue",
        user_message="спасибо",
        state_snapshot=_STATE,
        thread_state=_THREAD,
        knowledge_answer_guard={},
    )
    assert payload["diagnostic_center_role"] == "advisory_context_only"
    assert payload["planner_role"] == "advisory_context_only"
    assert payload["active_line_role"] == "advisory_context_only"


def test_self_intro_not_lecture_obligation() -> None:
    act = build_dialogue_act_resolution_v1(user_message="Давай знакомиться, меня зовут Асхат")
    obligation = build_answer_obligation_resolver_v1(
        dialogue_act_resolution=act,
        last_assistant_offer={},
        unanswered_question_state={},
        dialogue_style_state={},
        dialogue_policy={"profile": "mvp_free_dialogue", "profile_preset": "free_dialogue_default"},
    )
    assert act["dialogue_act"] == "self_intro"
    assert obligation["answer_obligation"] == "acknowledge_self_intro"


def test_repair_complaint_uses_last_unanswered_question() -> None:
    act = build_dialogue_act_resolution_v1(user_message="ты не ответил мне на вопрос")
    unanswered = build_unanswered_question_state_v1(
        previous_state={
            "version": "unanswered_question_tracker_v1",
            "last_direct_user_question": "что такое нейросталкинг?",
            "turn_index": 2,
            "answer_required": True,
            "answer_status": "pending",
            "reason": "direct_knowledge_question",
        },
        user_message="ты не ответил мне на вопрос",
        dialogue_act_resolution=act,
        turn_index=3,
    )
    obligation = build_answer_obligation_resolver_v1(
        dialogue_act_resolution=act,
        last_assistant_offer={},
        unanswered_question_state=unanswered,
        dialogue_style_state={},
        dialogue_policy={"profile": "mvp_free_dialogue", "profile_preset": "free_dialogue_default"},
    )
    assert act["dialogue_act"] == "repair_complaint"
    assert obligation["answer_obligation"] == "repair_and_answer_last_question"


def test_confirmation_to_last_offer() -> None:
    last_offer = build_last_assistant_offer_v1(
        previous_state=None,
        previous_assistant_message="Могу показать, как адаптировать технику под Красный, Оранжевый и Зеленый уровни.",
        dialogue_pragmatics={"is_contextual_followup": True},
    )
    act = build_dialogue_act_resolution_v1(
        user_message="да",
        dialogue_pragmatics={"is_contextual_followup": True},
        last_assistant_offer=last_offer,
    )
    obligation = build_answer_obligation_resolver_v1(
        dialogue_act_resolution=act,
        last_assistant_offer=last_offer,
        unanswered_question_state={},
        dialogue_style_state={},
        dialogue_policy={"profile": "mvp_free_dialogue", "profile_preset": "free_dialogue_default"},
    )
    assert act["dialogue_act"] == "confirmation_to_last_offer"
    assert obligation["answer_obligation"] == "answer_last_offer"


def test_confirmation_to_last_offer_for_plan_then_show_pattern() -> None:
    last_offer = build_last_assistant_offer_v1(
        previous_state=None,
        previous_assistant_message=(
            "Хорошо - предлагаю такой план, и потом покажу адаптацию под Красный, Оранжевый и Зеленый уровни. "
            "Скажи, что выбрать, и начнем."
        ),
        dialogue_pragmatics={"is_contextual_followup": True},
    )
    act = build_dialogue_act_resolution_v1(
        user_message="да",
        dialogue_pragmatics={"is_contextual_followup": True},
        last_assistant_offer=last_offer,
    )
    obligation = build_answer_obligation_resolver_v1(
        dialogue_act_resolution=act,
        last_assistant_offer=last_offer,
        unanswered_question_state={},
        dialogue_style_state={},
        dialogue_policy={"profile": "mvp_free_dialogue", "profile_preset": "free_dialogue_default"},
    )
    assert last_offer["is_open"] is True
    assert act["dialogue_act"] == "confirmation_to_last_offer"
    assert obligation["answer_obligation"] == "answer_last_offer"


def test_close_ack() -> None:
    act = build_dialogue_act_resolution_v1(user_message="спасибо")
    obligation = build_answer_obligation_resolver_v1(
        dialogue_act_resolution=act,
        last_assistant_offer={},
        unanswered_question_state={},
        dialogue_style_state={},
        dialogue_policy={"profile": "safe_guided", "profile_preset": "safe_guided"},
    )
    assert act["dialogue_act"] == "close_ack"
    assert obligation["answer_obligation"] == "close_gently"
