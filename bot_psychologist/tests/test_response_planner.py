from __future__ import annotations

from types import SimpleNamespace

from bot_agent.multiagent.response_planner import (
    RESPONSE_PLANNER_VERSION,
    build_response_planner_decision,
)


def _thread(**kwargs):
    base = {"response_mode": "reflect", "safety_active": False, "ok_position": "I+W+"}
    base.update(kwargs)
    return SimpleNamespace(**base)


def _state(**kwargs):
    base = {"safety_flag": False, "nervous_state": "window"}
    base.update(kwargs)
    return SimpleNamespace(**base)


def _guard(*, direct: bool = False, practice_allowed: bool = False):
    return {
        "knowledge_answer": {
            "needed": direct,
            "should_answer_directly": direct,
            "kb_grounding_available": direct,
        },
        "practice_gate": {"practice_allowed": practice_allowed},
    }


def _active_line(**kwargs):
    base = {
        "user_intent": "understand_mechanism",
        "continuity_mode": "continue_existing_line",
        "should_ask_question": True,
        "should_offer_practice": False,
        "revoicing_allowed": False,
        "repair_mode": None,
    }
    base.update(kwargs)
    return base


def test_planner_version_and_enabled_contract() -> None:
    decision = build_response_planner_decision(
        user_message="Хочу понять механизм",
        state_snapshot=_state(),
        thread_state=_thread(),
        diagnostic_card=None,
        active_line=_active_line(),
        knowledge_answer_guard=_guard(),
        philosophy_kernel={},
    )
    assert decision.version == RESPONSE_PLANNER_VERSION
    assert decision.enabled is True


def test_safety_overrides_regular_logic() -> None:
    decision = build_response_planner_decision(
        user_message="Мне очень плохо",
        state_snapshot=_state(safety_flag=True),
        thread_state=_thread(response_mode="safe_override", safety_active=True),
        diagnostic_card=None,
        active_line=_active_line(user_intent="short_support", should_offer_practice=True),
        knowledge_answer_guard=_guard(practice_allowed=True),
        philosophy_kernel={},
    )
    assert decision.next_move == "stabilize_safety"
    assert decision.answer_shape == "safety_grounding"
    assert decision.practice_policy == "required_for_safety_or_grounding"
    assert decision.question_policy == "none"
    assert decision.safety_priority is True


def test_correction_maps_to_repair_and_forbids_practice() -> None:
    decision = build_response_planner_decision(
        user_message="Почему ты предлагаешь практику?",
        state_snapshot=_state(),
        thread_state=_thread(),
        diagnostic_card=None,
        active_line=_active_line(
            user_intent="correction_of_bot",
            continuity_mode="repair_and_continue_line",
            repair_mode="acknowledge_and_return_to_mechanism",
            should_ask_question=False,
        ),
        knowledge_answer_guard=_guard(practice_allowed=False),
        philosophy_kernel={},
    )
    assert decision.next_move == "repair_misalignment"
    assert decision.answer_shape == "repair_acknowledgement"
    assert decision.practice_policy == "forbidden"
    assert decision.continuity_policy == "repair_and_continue"


def test_short_support_is_very_short_and_no_question() -> None:
    decision = build_response_planner_decision(
        user_message="Я устал, просто пару спокойных слов, без анализа.",
        state_snapshot=_state(nervous_state="hypo"),
        thread_state=_thread(response_mode="validate"),
        diagnostic_card=None,
        active_line=_active_line(user_intent="short_support", should_ask_question=False),
        knowledge_answer_guard=_guard(practice_allowed=False),
        philosophy_kernel={},
    )
    assert decision.next_move == "give_short_support"
    assert decision.response_depth == "very_short"
    assert decision.question_policy == "none"
    assert decision.practice_policy == "forbidden"


def test_known_concept_uses_direct_answer_path() -> None:
    decision = build_response_planner_decision(
        user_message="Что такое нейросталкинг?",
        state_snapshot=_state(),
        thread_state=_thread(),
        diagnostic_card=None,
        active_line=_active_line(user_intent="known_concept_question"),
        knowledge_answer_guard=_guard(direct=True, practice_allowed=False),
        philosophy_kernel={},
    )
    assert decision.next_move == "answer_known_concept"
    assert decision.answer_shape == "compact_direct"
    assert decision.question_policy == "none"
    assert decision.practice_policy == "forbidden"


def test_explicit_practice_respects_practice_gate() -> None:
    denied = build_response_planner_decision(
        user_message="Дай практику на сейчас",
        state_snapshot=_state(),
        thread_state=_thread(response_mode="practice"),
        diagnostic_card=None,
        active_line=_active_line(user_intent="ask_for_practice", should_offer_practice=False),
        knowledge_answer_guard=_guard(practice_allowed=False),
        philosophy_kernel={},
    )
    allowed = build_response_planner_decision(
        user_message="Дай практику на сейчас",
        state_snapshot=_state(),
        thread_state=_thread(response_mode="practice"),
        diagnostic_card=None,
        active_line=_active_line(
            user_intent="ask_for_practice",
            should_offer_practice=True,
            revoicing_allowed=True,
        ),
        knowledge_answer_guard=_guard(practice_allowed=True),
        philosophy_kernel={},
    )
    assert denied.practice_policy == "forbidden"
    assert denied.next_move == "clarify_one_point"
    assert allowed.practice_policy == "one_micro_step_allowed"
    assert allowed.next_move in {"give_practice", "give_direct_step"}


def test_active_line_no_question_becomes_planner_none() -> None:
    decision = build_response_planner_decision(
        user_message="Продолжи разбор механизма без вопросов",
        state_snapshot=_state(),
        thread_state=_thread(),
        diagnostic_card=None,
        active_line=_active_line(should_ask_question=False),
        knowledge_answer_guard=_guard(practice_allowed=False),
        philosophy_kernel={},
    )
    assert decision.question_policy == "none"
