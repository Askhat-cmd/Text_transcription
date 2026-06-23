from __future__ import annotations

from bot_agent.multiagent.runtime_trace_summary import build_runtime_trace_summary_v1


def test_runtime_trace_summary_reports_compact_latest_turn_controls() -> None:
    summary = build_runtime_trace_summary_v1(
        entrypoint="multiagent_adapter",
        final_answer_directive={
            "practice_policy": "forbidden_explicit_latest_turn",
            "depth": "short",
            "answer_shape": "direct_answer",
            "latest_turn_constraints_v1": {
                "version": "latest_turn_constraints_v1",
                "no_practice": True,
                "no_breathing_only": False,
                "simplify": True,
                "long_term_perspective": False,
                "no_internal_db": False,
                "active_constraints": ["no_practice", "simplify"],
                "source": "latest_user_turn_explicit_text",
            },
        },
        writer_debug={
            "writer_kb_payload_trace": {"payload_chunk_count": 0},
            "semantic_cards_pilot": {"writer_payload_enriched": False, "selected_card_count": 0},
        },
        overlay_shadow={
            "used_for_writer": False,
            "used_for_retrieval_execution": False,
            "used_for_final_answer": False,
        },
    )

    assert summary["entrypoint"] == "multiagent_adapter"
    assert summary["latest_turn_constraints"] == ["no_practice", "simplify"]
    assert summary["kb_visible_to_writer"] is False
    assert summary["semantic_cards_visible_to_writer"] is False
    assert summary["overlay_apply_detected"] is False
    assert summary["final_directive_mode"] == "answer_directly_without_practice"
    assert summary["practice_blocked_by_user_request"] is True
    assert summary["warnings"] == []
    assert summary["full_trace_available"] is True


def test_runtime_trace_summary_warns_if_no_internal_db_still_visible() -> None:
    summary = build_runtime_trace_summary_v1(
        entrypoint="multiagent_adapter",
        final_answer_directive={
            "practice_policy": "forbidden",
            "depth": "medium",
            "latest_turn_constraints_v1": {
                "version": "latest_turn_constraints_v1",
                "no_practice": False,
                "no_breathing_only": False,
                "simplify": False,
                "long_term_perspective": False,
                "no_internal_db": True,
                "active_constraints": ["no_internal_db"],
                "source": "latest_user_turn_explicit_text",
            },
        },
        writer_debug={
            "writer_kb_payload_trace": {"payload_chunk_count": 1},
            "semantic_cards_pilot": {"writer_payload_enriched": True, "selected_card_count": 1},
        },
        overlay_shadow={},
    )

    assert "no_internal_db_visible_payload_leak" in summary["warnings"]
