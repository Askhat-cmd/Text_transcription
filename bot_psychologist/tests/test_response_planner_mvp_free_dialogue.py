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


def _guard(**kwargs):
    knowledge = {
        "needed": False,
        "should_answer_directly": False,
        "kb_grounding_available": False,
        "concept": "",
    }
    knowledge.update(kwargs)
    return {
        "knowledge_answer": knowledge,
        "practice_gate": {"practice_allowed": False},
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


def test_mvp_expansion_request_triggers_long_explanation() -> None:
    decision = build_response_planner_decision(
        user_message="объясни развернуто и подробно",
        state_snapshot=_state(),
        thread_state=_thread(),
        diagnostic_card=None,
        active_line=_active_line(),
        knowledge_answer_guard=_guard(),
        philosophy_kernel={},
        dialogue_policy={"profile": "mvp_free_dialogue", "expansion_requested": True},
    )
    assert decision.answer_shape == "expanded_explanation"
    assert decision.response_depth == "long"
    assert decision.question_policy == "none"


def test_mvp_known_concept_followup_inherits_and_goes_deep() -> None:
    decision = build_response_planner_decision(
        user_message="я не понял, объясни нормально и подробно",
        state_snapshot=_state(),
        thread_state=_thread(),
        diagnostic_card=None,
        active_line=_active_line(user_intent="known_concept_question"),
        knowledge_answer_guard=_guard(needed=True, should_answer_directly=True, kb_grounding_available=True, concept="нейросталкинг"),
        philosophy_kernel={},
        dialogue_policy={
            "profile": "mvp_free_dialogue",
            "expansion_requested": True,
            "repair_and_expand_requested": True,
            "active_concept": "нейросталкинг",
        },
    )
    assert decision.answer_shape == "repair_and_expand"
    assert decision.response_depth == "long"


def test_mvp_hypo_without_low_resource_text_does_not_force_short_support() -> None:
    decision = build_response_planner_decision(
        user_message="в разговоре на месте",
        state_snapshot=_state(nervous_state="hypo"),
        thread_state=_thread(),
        diagnostic_card=None,
        active_line=_active_line(),
        knowledge_answer_guard=_guard(),
        philosophy_kernel={},
        dialogue_policy={"profile": "mvp_free_dialogue"},
    )
    assert decision.answer_shape != "short_support"

