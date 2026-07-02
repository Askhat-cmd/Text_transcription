from __future__ import annotations

from types import SimpleNamespace

from bot_agent.multiagent.final_answer_directive import build_final_answer_directive_v1
from bot_agent.multiagent.runtime_trace_summary import build_runtime_trace_summary_v1


def _directive(user_message: str) -> dict:
    return build_final_answer_directive_v1(
        user_message=user_message,
        dialogue_policy={"profile": "mvp_free_dialogue"},
        dialogue_pragmatics={},
        response_planner={"answer_shape": "compact_direct", "practice_policy": "allowed_explicit_request"},
        active_line={},
        diagnostic_card={},
        diagnostic_center_shadow={},
        retrieval_decision={},
        knowledge_answer_guard={},
        thread_state=SimpleNamespace(safety_active=False),
        state_snapshot=SimpleNamespace(safety_flag=False),
    ).to_dict()


def test_no_practice_boundary_trace_acknowledges_directive_hardening() -> None:
    directive = _directive("Объясни, почему я злюсь на себя, но без практик и упражнений.")

    boundary = directive["boundary_trace_v1"]

    assert directive["latest_turn_constraints_v1"]["no_practice"] is True
    assert directive["practice_policy"] == "forbidden_explicit_latest_turn"
    assert boundary["boundary_flags"] == ["no_practice"]
    assert boundary["latest_turn_constraints"]["no_practice"] is True
    assert boundary["writer_directive_ack"]["no_practice"] is True
    assert boundary["applied_suppressions"]["practice_suggestion_suppressed"] is True


def test_runtime_trace_summary_exposes_no_practice_boundary_contract() -> None:
    directive = _directive("Объясни, почему я злюсь на себя, но без практик и упражнений.")
    summary = build_runtime_trace_summary_v1(
        entrypoint="multiagent_adapter",
        final_answer_directive=directive,
        writer_debug={
            "writer_grounding_visibility_v1": {
                "kb_visible_to_writer": False,
                "semantic_cards_visible_to_writer": False,
                "reason": "support_or_pushback_turn_trace_only",
            },
            "writer_kb_payload_trace": {
                "payload_chunk_count": 0,
                "status": "trace_only",
            },
            "runtime_truth_trace_v1": {
                "writer_visible_payload_count": 0,
                "grounding_visibility_reason": "support_or_pushback_turn_trace_only",
                "payload_decision_reason": "trace_only",
            },
        },
        overlay_shadow={},
        user_message="Объясни, почему я злюсь на себя, но без практик и упражнений.",
        dialogue_act_resolution={},
        retrieval_decision={"retrieval_action": "query_kb", "retrieval_need": "knowledge_context"},
        hybrid_retrieval_plan={},
    )

    boundary = summary["boundary_trace_v1"]

    assert summary["practice_blocked_by_user_request"] is True
    assert boundary["boundary_flags"] == ["no_practice"]
    assert boundary["latest_turn_constraints"]["no_practice"] is True
    assert boundary["writer_directive_ack"]["no_practice"] is True
    assert boundary["applied_suppressions"]["practice_suggestion_suppressed"] is True
    assert summary["runtime_truth_trace_v1"]["boundary_trace_v1"] == boundary
