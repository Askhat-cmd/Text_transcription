from __future__ import annotations

from types import SimpleNamespace

from bot_agent.multiagent.response_planner import build_response_planner_decision


def _thread(**kwargs):
    base = {"response_mode": "reflect", "safety_active": False, "ok_position": "I+W+"}
    base.update(kwargs)
    return SimpleNamespace(**base)


def _state(**kwargs):
    base = {"safety_flag": False, "nervous_state": "window"}
    base.update(kwargs)
    return SimpleNamespace(**base)


def _guard() -> dict:
    return {
        "knowledge_answer": {
            "needed": True,
            "concept": "нейросталкинг",
            "should_answer_directly": True,
            "kb_grounding_available": True,
            "answer_type": "practice_overview",
        },
        "practice_gate": {"practice_allowed": True},
    }


def _active_line() -> dict:
    return {
        "user_intent": "understand_mechanism",
        "continuity_mode": "continue_existing_line",
        "should_ask_question": False,
        "should_offer_practice": False,
        "revoicing_allowed": False,
        "repair_mode": None,
    }


def test_mvp_practice_overview_is_long_catalog_not_one_step() -> None:
    decision = build_response_planner_decision(
        user_message="скажи, а в нейросталкинге какие практики предлагаются чтобы это видеть",
        state_snapshot=_state(),
        thread_state=_thread(),
        diagnostic_card=None,
        active_line=_active_line(),
        knowledge_answer_guard=_guard(),
        philosophy_kernel={},
        dialogue_policy={
            "profile": "mvp_free_dialogue",
            "practice_overview_requested": True,
            "explicit_one_step_requested": False,
        },
    )
    assert decision.next_move == "answer_practice_overview"
    assert decision.answer_shape == "practice_catalog_explanation"
    assert decision.response_depth == "long"
    assert decision.practice_policy == "overview_allowed"


def test_explicit_one_step_still_keeps_one_step() -> None:
    decision = build_response_planner_decision(
        user_message="дай один конкретный шаг прямо сейчас",
        state_snapshot=_state(),
        thread_state=_thread(),
        diagnostic_card=None,
        active_line=_active_line(),
        knowledge_answer_guard=_guard(),
        philosophy_kernel={},
        dialogue_policy={
            "profile": "mvp_free_dialogue",
            "explicit_one_step_requested": True,
        },
    )
    assert decision.answer_shape == "one_step"
