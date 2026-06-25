from __future__ import annotations

from types import SimpleNamespace

from bot_agent.multiagent.final_answer_directive import build_final_answer_directive_v1
from bot_agent.multiagent.runtime_trace_summary import build_runtime_trace_summary_v1


def _state() -> SimpleNamespace:
    return SimpleNamespace(safety_flag=False)


def _thread() -> SimpleNamespace:
    return SimpleNamespace(safety_active=False)


def test_greeting_turn_gets_contact_brief_shape_profile() -> None:
    directive = build_final_answer_directive_v1(
        user_message="Привет! Я Олег.",
        dialogue_policy={
            "profile": "mvp_free_dialogue",
            "profile_preset": "free_dialogue_default",
            "dialogue_act_resolution": {"dialogue_act": "greeting"},
        },
        dialogue_pragmatics={},
        response_planner={},
        active_line={},
        diagnostic_card={},
        diagnostic_center_shadow={},
        retrieval_decision={},
        knowledge_answer_guard={},
        thread_state=_thread(),
        state_snapshot=_state(),
        answer_obligation_resolution={
            "dialogue_act": "greeting",
            "answer_obligation": "continue_thread",
            "answer_shape": "simple_contact",
            "question_policy": "optional_none",
            "depth": "short",
        },
        unified_dialogue_profile={},
    ).to_dict()

    assert directive["answer_shape_profile"] == "contact_brief"
    assert directive["depth"] == "short"
    assert any("warm and brief" in note for note in directive["answer_shape_profile_notes"])


def test_compact_direct_question_gets_ordinary_explanation_profile() -> None:
    directive = build_final_answer_directive_v1(
        user_message="Как преодолеть свое сопротивление, когда приходится общаться с неприятными людьми?",
        dialogue_policy={
            "profile": "mvp_free_dialogue",
            "profile_preset": "free_dialogue_default",
            "compact_support_answer": True,
            "dialogue_act_resolution": {"dialogue_act": "direct_question"},
        },
        dialogue_pragmatics={},
        response_planner={
            "answer_shape": "mechanism_explanation",
            "question_policy": "optional_none",
            "practice_policy": "forbidden",
        },
        active_line={},
        diagnostic_card={},
        diagnostic_center_shadow={},
        retrieval_decision={},
        knowledge_answer_guard={},
        thread_state=_thread(),
        state_snapshot=_state(),
        answer_obligation_resolution={
            "dialogue_act": "direct_question",
            "answer_obligation": "answer_direct_question",
            "answer_shape": "direct_answer",
            "question_policy": "optional_none",
            "depth": "medium",
        },
        unified_dialogue_profile={},
    ).to_dict()

    assert directive["answer_shape_profile"] == "ordinary_explanation_compact"
    assert any("direct answer" in note.lower() for note in directive["answer_shape_profile_notes"])
    assert any("mini-lecture" in boundary.lower() for boundary in directive["hard_boundaries"])


def test_no_internal_db_profile_outranks_direct_source_profile() -> None:
    directive = build_final_answer_directive_v1(
        user_message="Без внутренней базы, просто объясни своими словами, что это значит.",
        dialogue_policy={
            "profile": "mvp_free_dialogue",
            "profile_preset": "free_dialogue_default",
            "compact_support_answer": True,
            "dialogue_act_resolution": {"dialogue_act": "knowledge_question"},
        },
        dialogue_pragmatics={},
        response_planner={
            "answer_shape": "compact_direct",
            "question_policy": "none",
            "practice_policy": "forbidden",
        },
        active_line={},
        diagnostic_card={},
        diagnostic_center_shadow={},
        retrieval_decision={"direct_source_request": True},
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

    assert directive["answer_shape_profile"] == "no_internal_db_compact"


def test_non_source_knowledge_question_stays_in_ordinary_compact_profile() -> None:
    directive = build_final_answer_directive_v1(
        user_message="Почему меня так задевает враньё?",
        dialogue_policy={
            "profile": "mvp_free_dialogue",
            "profile_preset": "free_dialogue_default",
            "compact_support_answer": True,
            "dialogue_act_resolution": {"dialogue_act": "knowledge_question"},
        },
        dialogue_pragmatics={},
        response_planner={
            "answer_shape": "compact_direct",
            "question_policy": "optional_none",
            "practice_policy": "forbidden",
        },
        active_line={},
        diagnostic_card={},
        diagnostic_center_shadow={},
        retrieval_decision={},
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

    assert directive["answer_shape_profile"] == "ordinary_explanation_compact"


def test_direct_source_request_detected_from_live_message_shape() -> None:
    directive = build_final_answer_directive_v1(
        user_message="Что во внутренней базе говорится про программу «несовершенное Я» и пять драйверов?",
        dialogue_policy={
            "profile": "mvp_free_dialogue",
            "profile_preset": "free_dialogue_default",
            "dialogue_act_resolution": {"dialogue_act": "knowledge_question"},
        },
        dialogue_pragmatics={},
        response_planner={
            "answer_shape": "structured_explanation",
            "question_policy": "optional_none",
            "practice_policy": "forbidden",
        },
        active_line={},
        diagnostic_card={},
        diagnostic_center_shadow={},
        retrieval_decision={
            "retrieval_action": "query_kb",
            "composer": {"reason": "knowledge question needs compact KB support"},
            "contextual_retrieval_query_composer": {
                "reason": "knowledge question needs compact KB support",
            },
        },
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


def test_dialogue_act_direct_question_still_compacts_when_fallback_obligation_name_is_old() -> None:
    directive = build_final_answer_directive_v1(
        user_message="Как преодолеть сопротивление, когда нужно общаться с неприятными людьми?",
        dialogue_policy={
            "profile": "mvp_free_dialogue",
            "profile_preset": "free_dialogue_default",
            "dialogue_act_resolution": {"dialogue_act": "direct_question"},
        },
        dialogue_pragmatics={},
        response_planner={
            "answer_shape": "direct_answer",
            "question_policy": "optional_none",
            "practice_policy": "forbidden",
        },
        active_line={},
        diagnostic_card={},
        diagnostic_center_shadow={},
        retrieval_decision={},
        knowledge_answer_guard={},
        thread_state=_thread(),
        state_snapshot=_state(),
        answer_obligation_resolution={
            "dialogue_act": "direct_question",
            "answer_obligation": "answer_user_question_directly",
            "answer_shape": "direct_answer",
            "question_policy": "optional_none",
            "depth": "medium",
        },
        unified_dialogue_profile={},
    ).to_dict()

    assert directive["answer_shape_profile"] == "ordinary_explanation_compact"


def test_question_mark_fallback_still_compacts_when_runtime_act_is_missing() -> None:
    directive = build_final_answer_directive_v1(
        user_message="Как преодолеть сопротивление, когда нужно общаться с неприятными людьми?",
        dialogue_policy={
            "profile": "mvp_free_dialogue",
            "profile_preset": "free_dialogue_default",
        },
        dialogue_pragmatics={},
        response_planner={
            "answer_shape": "direct_answer",
            "question_policy": "optional_none",
            "practice_policy": "forbidden",
        },
        active_line={},
        diagnostic_card={},
        diagnostic_center_shadow={},
        retrieval_decision={},
        knowledge_answer_guard={},
        thread_state=_thread(),
        state_snapshot=_state(),
        answer_obligation_resolution={},
        unified_dialogue_profile={},
    ).to_dict()

    assert directive["answer_shape_profile"] == "ordinary_explanation_compact"


def test_runtime_trace_summary_exposes_selected_answer_shape_profile() -> None:
    summary = build_runtime_trace_summary_v1(
        entrypoint="multiagent_adapter",
        final_answer_directive={
            "answer_obligation": "answer_direct_question",
            "answer_shape": "direct_answer",
            "answer_shape_profile": "ordinary_explanation_compact",
            "answer_shape_profile_notes": [
                "Start with a direct answer in the first one or two sentences.",
                "Name only one main mechanism in simple words.",
            ],
            "latest_turn_constraints_v1": {
                "version": "latest_turn_constraints_v1",
                "active_constraints": [],
            },
        },
        writer_debug={},
        overlay_shadow={},
    )

    assert summary["selected_answer_shape_profile"] == "ordinary_explanation_compact"
    assert summary["answer_shape_profile_notes"][0].startswith("Start with a direct answer")
