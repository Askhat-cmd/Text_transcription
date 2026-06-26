from __future__ import annotations

from types import SimpleNamespace

from bot_agent.multiagent.final_answer_directive import build_final_answer_directive_v1
from bot_agent.multiagent.response_planner import build_response_planner_decision


def _state(*, safety_flag: bool = False) -> SimpleNamespace:
    return SimpleNamespace(safety_flag=safety_flag, nervous_state="window")


def _thread(*, safety_active: bool = False) -> SimpleNamespace:
    return SimpleNamespace(safety_active=safety_active, response_mode="reflect", ok_position="I+W+", nervous_state="window")


def test_wake_depth_reference_biases_mechanism_to_protective_function() -> None:
    decision = build_response_planner_decision(
        user_message="Почему меня так задевает враньё?",
        state_snapshot=_state(),
        thread_state=_thread(),
        diagnostic_card=None,
        active_line={
            "user_intent": "understand_mechanism",
            "continuity_mode": "continue_existing_line",
            "should_ask_question": False,
            "should_offer_practice": False,
            "revoicing_allowed": False,
        },
        knowledge_answer_guard={},
        philosophy_kernel={},
        dialogue_policy={"profile": "mvp_free_dialogue", "profile_preset": "free_dialogue_default"},
    ).to_dict()

    assert decision["next_move"] == "deepen_mechanism"
    assert "назвать один механизм" in decision["must_include"]
    assert "показать что он защищает" in decision["must_include"]
    assert any("базе" in item or "semantic cards" in item for item in decision["must_avoid"])


def test_panic_depth_reference_keeps_safety_first() -> None:
    directive = build_final_answer_directive_v1(
        user_message="У моей жены бывают панические атаки. Как мне ей помочь?",
        dialogue_policy={
            "profile": "mvp_free_dialogue",
            "profile_preset": "free_dialogue_default",
            "dialogue_act_resolution": {"dialogue_act": "support_request"},
        },
        dialogue_pragmatics={},
        response_planner={"answer_shape": "safety_grounding", "question_policy": "none", "practice_policy": "required_for_safety_or_grounding"},
        active_line={},
        diagnostic_card={},
        diagnostic_center_shadow={},
        retrieval_decision={},
        knowledge_answer_guard={},
        thread_state=_thread(safety_active=True),
        state_snapshot=_state(safety_flag=True),
        answer_obligation_resolution={
            "dialogue_act": "support_request",
            "answer_obligation": "answer_latest_turn",
            "answer_shape": "simple_contact",
            "question_policy": "none",
            "depth": "short",
        },
        unified_dialogue_profile={},
    ).to_dict()

    notes = directive["answer_shape_profile_notes"]
    assert directive["answer_shape_profile"] == "safety_grounding_compact"
    assert any("stabilize first" in note.lower() for note in notes)
    assert any("universal fix" in note.lower() for note in notes)


def test_direct_source_shape_reframes_as_specialist_explanation_not_storage_report() -> None:
    directive = build_final_answer_directive_v1(
        user_message="А что у тебя в базе говорится про панические атаки?",
        dialogue_policy={
            "profile": "mvp_free_dialogue",
            "profile_preset": "free_dialogue_default",
            "dialogue_act_resolution": {"dialogue_act": "knowledge_question"},
        },
        dialogue_pragmatics={},
        response_planner={"answer_shape": "structured_explanation", "question_policy": "optional_none", "practice_policy": "forbidden"},
        active_line={},
        diagnostic_card={},
        diagnostic_center_shadow={},
        retrieval_decision={"direct_source_request": True, "retrieval_action": "query_kb"},
        knowledge_answer_guard={},
        thread_state=_thread(),
        state_snapshot=_state(),
        answer_obligation_resolution={
            "dialogue_act": "knowledge_question",
            "answer_obligation": "answer_knowledge_question",
            "answer_shape": "structured_explanation",
            "question_policy": "optional_none",
            "depth": "medium",
        },
        unified_dialogue_profile={},
    ).to_dict()

    assert directive["answer_shape_profile"] == "direct_kb_grounded_compact"
    assert any("storage or chunk report" in note.lower() for note in directive["answer_shape_profile_notes"])
