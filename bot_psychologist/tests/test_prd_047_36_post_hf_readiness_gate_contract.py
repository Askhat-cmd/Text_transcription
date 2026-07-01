from bot_psychologist.tools.run_prd_047_36_post_hf_owner_readiness_gate import (
    classify_g1_trace_reload,
    classify_g3_direct_concept_followup,
    classify_overall,
)


def test_g1_trace_reload_passes_when_counts_match_and_reload_keeps_trace() -> None:
    verdict, reasons, evidence = classify_g1_trace_reload(
        {
            "pre_restart": {
                "browser": {
                    "before_reload": {"pipeline_count": 5, "trace_unavailable_count": 0},
                    "after_reload": {
                        "trace_unavailable_count": 0,
                        "has_requested_turn_missing": False,
                        "has_trace_expired_reason": False,
                    },
                },
                "history_turns": [1, 2, 3, 4, 5],
                "trace_checks": {
                    f"turn_{index}": {
                        "status_code": 200,
                        "availability": {"exact_turn_match": True},
                    }
                    for index in range(1, 6)
                },
            },
            "post_restart": {
                "old_session_trace_check": {
                    "availability": {"reason_code": "debug_trace_expired_after_backend_restart"}
                }
            },
            "frontend_status": 200,
        }
    )

    assert verdict == "PASS"
    assert reasons == []
    assert evidence["available_exact_trace_turns"] == 5


def test_g3_followup_blocks_when_selected_knowledge_stays_trace_only() -> None:
    verdict, reasons = classify_g3_direct_concept_followup(
        {
            "trace_available": True,
            "contains_internal_language": False,
            "selected_card_ids": ["program_imperfect_self_v1"],
            "writer_payload_count": 0,
            "selected_card_status": "trace_only",
            "grounding_reason": "no_clear_retrieval_need",
            "writer_can_ignore_grounding": True,
        }
    )

    assert verdict == "BLOCKER"
    assert reasons == ["selected_relevant_knowledge_not_delivered"]


def test_overall_becomes_accepted_with_warning_without_blockers() -> None:
    verdict = classify_overall(
        [
            {"scenario_id": "G1", "verdict": "PASS"},
            {"scenario_id": "G2", "verdict": "PASS_WITH_WARNING"},
            {"scenario_id": "G3", "verdict": "PASS"},
        ]
    )

    assert verdict == "ACCEPTED_WITH_WARNING"
