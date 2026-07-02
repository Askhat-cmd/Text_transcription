from __future__ import annotations

from bot_agent.multiagent.boundary_trace import build_boundary_trace_v1
from bot_psychologist.tools.run_prd_047_36_post_hf_owner_readiness_gate import _extract_boundary_trace


def test_boundary_trace_contract_marks_combined_latest_turn_constraints() -> None:
    payload = build_boundary_trace_v1(
        latest_turn_constraints={
            "no_internal_db": True,
            "no_practice": True,
            "no_breathing_only": False,
            "simplify": False,
            "source": "latest_user_turn_explicit_text",
        },
        writer_grounding_visibility={
            "kb_visible_to_writer": False,
            "semantic_cards_visible_to_writer": False,
            "reason": "latest_turn_no_internal_db",
        },
        writer_kb_payload_trace={"payload_chunk_count": 0, "status": "suppressed"},
        final_answer_directive={"practice_policy": "forbidden_explicit_latest_turn"},
        runtime_truth_trace={
            "writer_visible_payload_count": 0,
            "grounding_visibility_reason": "latest_turn_no_internal_db",
        },
    )

    assert payload["boundary_flags"] == ["no_internal_db", "no_practice"]
    assert payload["latest_turn_constraints"]["no_internal_db"] is True
    assert payload["latest_turn_constraints"]["no_practice"] is True
    assert payload["boundary_sources"]["no_internal_db"] == "latest_user_request"
    assert payload["boundary_sources"]["no_practice"] == "latest_user_request"
    assert payload["applied_suppressions"]["writer_kb_payload_suppressed"] is True
    assert payload["applied_suppressions"]["semantic_cards_writer_visible_suppressed"] is True
    assert payload["applied_suppressions"]["practice_suggestion_suppressed"] is True
    assert payload["writer_directive_ack"]["no_internal_db"] is True
    assert payload["writer_directive_ack"]["no_practice"] is True


def test_post_hf_gate_extracts_nested_boundary_trace_from_runtime_summary() -> None:
    boundary_trace = {"boundary_flags": ["no_internal_db"], "latest_turn_constraints": {"no_internal_db": True}}
    payload = _extract_boundary_trace(
        {
            "runtime_trace_summary_v1": {
                "boundary_trace_v1": boundary_trace,
            }
        }
    )

    assert payload == boundary_trace


def test_greeting_trace_is_not_mislabeled_as_boundary_request() -> None:
    payload = build_boundary_trace_v1(
        latest_turn_constraints={},
        writer_grounding_visibility={
            "kb_visible_to_writer": False,
            "semantic_cards_visible_to_writer": False,
            "reason": "greeting_or_contact",
        },
        writer_kb_payload_trace={"payload_chunk_count": 0, "status": "suppressed"},
        runtime_truth_trace={
            "writer_visible_payload_count": 0,
            "grounding_visibility_reason": "greeting_or_contact",
        },
    )

    assert payload["boundary_flags"] == []
    assert payload["boundary_sources"]["no_internal_db"] == "not_detected"
    assert payload["boundary_sources"]["no_practice"] == "not_detected"
