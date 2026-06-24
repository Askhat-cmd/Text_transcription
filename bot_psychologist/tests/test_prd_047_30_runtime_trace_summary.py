from __future__ import annotations

from bot_agent.multiagent.runtime_trace_summary import build_runtime_trace_summary_v1


def test_runtime_trace_summary_prefers_writer_grounding_visibility_flags() -> None:
    summary = build_runtime_trace_summary_v1(
        entrypoint="multiagent_adapter",
        final_answer_directive={
            "practice_policy": "forbidden",
            "depth": "short",
            "answer_shape": "direct_answer",
            "latest_turn_constraints_v1": {
                "version": "latest_turn_constraints_v1",
                "no_practice": False,
                "no_breathing_only": False,
                "simplify": True,
                "long_term_perspective": False,
                "no_internal_db": False,
                "active_constraints": ["simplify"],
                "source": "latest_user_turn_explicit_text",
            },
        },
        writer_debug={
            "writer_grounding_visibility_v1": {
                "version": "writer_grounding_visibility_v1",
                "kb_visible_to_writer": False,
                "semantic_cards_visible_to_writer": False,
                "reason": "simplify_turn_trace_only",
            },
            "writer_kb_payload_trace": {"payload_chunk_count": 1},
            "semantic_cards_pilot": {"writer_payload_enriched": True, "selected_card_count": 1},
        },
        overlay_shadow={},
    )

    assert summary["writer_grounding_visibility_v1"]["reason"] == "simplify_turn_trace_only"
    assert summary["kb_visible_to_writer"] is False
    assert summary["semantic_cards_visible_to_writer"] is False
    assert "writer_grounding_visibility_payload_mismatch" in summary["warnings"]
    assert "writer_grounding_visibility_semantic_mismatch" in summary["warnings"]


def test_runtime_trace_summary_marks_explicit_practice_request_note() -> None:
    summary = build_runtime_trace_summary_v1(
        entrypoint="multiagent_adapter",
        final_answer_directive={
            "answer_obligation": "provide_one_bounded_practice",
            "answer_shape": "one_short_practice",
            "latest_turn_constraints_v1": {
                "version": "latest_turn_constraints_v1",
                "active_constraints": [],
            },
        },
        writer_debug={
            "writer_grounding_visibility_v1": {
                "version": "writer_grounding_visibility_v1",
                "kb_visible_to_writer": True,
                "semantic_cards_visible_to_writer": True,
                "reason": "explicit_practice_request_narrow_grounding",
                "explicit_practice_request": True,
            },
            "writer_kb_payload_trace": {"payload_chunk_count": 1},
            "semantic_cards_pilot": {"writer_payload_enriched": False, "selected_card_count": 0},
        },
        overlay_shadow={},
    )

    assert summary["explicit_practice_request"] is True
    assert summary["practice_request_runtime_note"] == (
        "Detected explicit practice request. Forced contextual practice answer. "
        "KB remains optional/narrow."
    )
