from __future__ import annotations

from types import SimpleNamespace

from bot_agent.multiagent.response_planner import (
    build_response_planner_decision,
    detect_close_text,
    detect_explicit_practice_or_step_request,
    detect_low_resource_text,
    detect_no_question_request,
    detect_soft_distress_text,
    detect_world_blame_defensive_text,
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


def test_detectors_cover_required_groups() -> None:
    assert detect_low_resource_text("Я схлопнулся и не тяну длинные ответы") is True
    assert detect_soft_distress_text("Мне очень плохо, не выдерживаю") is True
    assert detect_world_blame_defensive_text("Люди тормозят, мир не понимает") is True
    assert detect_no_question_request("Продолжи без вопросов") is True
    assert detect_close_text("Спасибо") is True

    action = detect_explicit_practice_or_step_request("Дай один шаг прямо сейчас")
    assert action["wants_step"] is True
    assert action["wants_action"] is True


def test_low_resource_override_prefers_short_support() -> None:
    decision = build_response_planner_decision(
        user_message="Я как будто схлопнулся и пустой, не тяну длинные ответы.",
        state_snapshot=_state(),
        thread_state=_thread(),
        diagnostic_card=None,
        active_line=_active_line(user_intent="understand_mechanism"),
        knowledge_answer_guard=_guard(practice_allowed=False),
        philosophy_kernel={},
    )
    assert decision.next_move == "give_short_support"
    assert decision.answer_shape == "short_support"
    assert decision.question_policy == "none"


def test_soft_distress_override_prefers_safety_shape() -> None:
    decision = build_response_planner_decision(
        user_message="Мне сейчас очень плохо, не вывожу.",
        state_snapshot=_state(safety_flag=False),
        thread_state=_thread(safety_active=False),
        diagnostic_card=None,
        active_line=_active_line(user_intent="understand_mechanism"),
        knowledge_answer_guard=_guard(practice_allowed=False),
        philosophy_kernel={},
    )
    assert decision.next_move == "stabilize_safety"
    assert decision.answer_shape == "safety_grounding"


def test_thanks_text_override_closes_even_if_upstream_intent_wrong() -> None:
    decision = build_response_planner_decision(
        user_message="Спасибо.",
        state_snapshot=_state(),
        thread_state=_thread(),
        diagnostic_card=None,
        active_line=_active_line(user_intent="understand_mechanism"),
        knowledge_answer_guard=_guard(practice_allowed=False),
        philosophy_kernel={},
    )
    assert decision.next_move == "close_gently"
    assert decision.continuity_policy == "close_without_new_loop"


def test_explicit_step_request_uses_one_step_when_gate_allows() -> None:
    decision = build_response_planner_decision(
        user_message="Дай один шаг, что сделать прямо сейчас.",
        state_snapshot=_state(),
        thread_state=_thread(response_mode="practice"),
        diagnostic_card=None,
        active_line=_active_line(user_intent="understand_mechanism", should_offer_practice=False),
        knowledge_answer_guard=_guard(practice_allowed=True),
        philosophy_kernel={},
    )
    assert decision.next_move == "give_direct_step"
    assert decision.answer_shape == "one_step"
    assert decision.practice_policy == "one_micro_step_allowed"
