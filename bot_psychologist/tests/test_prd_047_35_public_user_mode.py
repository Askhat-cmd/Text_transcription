from __future__ import annotations

import json
from types import SimpleNamespace

from bot_agent.multiagent.final_answer_directive import build_final_answer_directive_v1
from bot_agent.multiagent.legacy_advisory_sanitizer import sanitize_legacy_advisory_for_writer
from bot_agent.multiagent.runtime_trace_summary import build_runtime_trace_summary_v1


def _state() -> SimpleNamespace:
    return SimpleNamespace(safety_flag=False)


def _thread() -> SimpleNamespace:
    return SimpleNamespace(safety_active=False)


def test_public_user_mode_directive_keeps_hidden_competence_and_no_internal_language() -> None:
    directive = build_final_answer_directive_v1(
        user_message="Почему меня так задевает враньё?",
        dialogue_policy={
            "profile": "mvp_free_dialogue",
            "profile_preset": "free_dialogue_default",
            "compact_support_answer": True,
            "dialogue_act_resolution": {"dialogue_act": "direct_question"},
        },
        dialogue_pragmatics={},
        response_planner={"answer_shape": "direct_answer", "question_policy": "optional_none", "practice_policy": "forbidden"},
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

    notes = directive["answer_shape_profile_notes"]
    assert directive["answer_shape_profile"] == "ordinary_explanation_compact"
    assert any("protect" in note.lower() for note in notes)
    assert any("one question or one step" in note.lower() for note in notes)
    assert any("internal db" in note.lower() for note in notes)


def test_public_user_mode_sanitizer_exports_hidden_competence_and_wake_reference() -> None:
    payload = sanitize_legacy_advisory_for_writer(
        {
            "writer_grounding_visibility_v1": {
                "kb_visible_to_writer": False,
                "semantic_cards_visible_to_writer": False,
                "reason": "non_kb_emotional_support_turn",
            },
            "hidden_knowledge_competence_v1": {
                "version": "hidden_knowledge_competence_v1",
                "public_user_mode": True,
                "owner_debug_question_detected": True,
                "user_facing_db_language_suppressed": True,
                "knowledge_used_as_hidden_lens": True,
                "raw_kb_dump_allowed": False,
                "reason": "owner_debug",
            },
        }
    )

    directive_payload = json.loads(payload["writer_visible_final_answer_directive_json"])

    assert directive_payload["hidden_knowledge_competence"]["public_user_mode"] is True
    assert directive_payload["hidden_knowledge_competence"]["owner_debug_question_detected"] is True
    assert directive_payload["hidden_knowledge_competence"]["raw_kb_dump_allowed"] is False
    assert directive_payload["wake_depth_reference"]["style_copy_forbidden"] is True
    assert directive_payload["wake_depth_reference"]["one_main_mechanism"] is True
    assert "hidden competence" in payload["writer_visible_summary"].lower()


def test_runtime_trace_summary_builds_hidden_competence_fallback_for_no_internal_db() -> None:
    summary = build_runtime_trace_summary_v1(
        entrypoint="multiagent_adapter",
        final_answer_directive={
            "latest_turn_constraints_v1": {
                "version": "latest_turn_constraints_v1",
                "no_internal_db": True,
                "active_constraints": ["no_internal_db"],
            },
            "answer_shape": "direct_answer",
            "practice_policy": "forbidden",
        },
        writer_debug={
            "writer_grounding_visibility_v1": {
                "kb_visible_to_writer": False,
                "semantic_cards_visible_to_writer": False,
                "reason": "latest_turn_no_internal_db",
                "no_internal_db": True,
            }
        },
        overlay_shadow={},
    )

    hidden = summary["hidden_knowledge_competence_v1"]
    assert hidden["public_user_mode"] is True
    assert hidden["user_facing_db_language_suppressed"] is True
    assert hidden["reason"] == "no_internal_db"
