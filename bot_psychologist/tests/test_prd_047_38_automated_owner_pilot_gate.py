from bot_psychologist.tools.run_prd_047_38_automated_owner_pilot_gate import (
    _classify_turn,
    _overall_verdict,
)


def _base_record(kind: str = "support") -> dict:
    return {
        "kind": kind,
        "trace_available": True,
        "public_internal_language_leak": False,
        "answer_char_count": 80,
        "answer_preview": "Короткий безопасный ответ.",
        "actionable_practice_detected": False,
        "safety_stabilization_detected": True,
        "deep_theory_detected": False,
        "trace_summary": {
            "writer_payload_count": 0,
            "selected_card_ids": [],
            "grounding_reason": "support_or_pushback_turn_trace_only",
            "boundary_flags": [],
            "semantic_cards_visible_to_writer": False,
        },
        "delivery_integrity": {
            "writer_api_match": True,
            "api_memory_match": True,
            "must_quarantine_answer": False,
        },
    }


def test_no_internal_db_payload_or_cards_is_blocker() -> None:
    record = _base_record("no_internal_db")
    record["trace_summary"]["boundary_flags"] = ["no_internal_db"]
    record["trace_summary"]["writer_payload_count"] = 1

    verdict, reasons = _classify_turn(record)

    assert verdict == "BLOCKER"
    assert "B5_no_internal_db_payload_or_cards_visible" in reasons


def test_concept_followup_selected_knowledge_with_payload_passes() -> None:
    record = _base_record("concept_followup")
    record["trace_summary"]["writer_payload_count"] = 2
    record["trace_summary"]["selected_card_ids"] = ["program_imperfect_self_v1"]
    record["trace_summary"]["grounding_reason"] = "direct_concept_followup"

    verdict, reasons = _classify_turn(record)

    assert verdict == "PASS"
    assert reasons == []


def test_no_practice_actionable_practice_is_blocker() -> None:
    record = _base_record("no_practice")
    record["trace_summary"]["boundary_flags"] = ["no_practice"]
    record["actionable_practice_detected"] = True

    verdict, reasons = _classify_turn(record)

    assert verdict == "BLOCKER"
    assert "B6_actionable_practice_detected" in reasons


def test_overall_warning_without_blockers_accepts_with_warnings() -> None:
    assert _overall_verdict(
        [
            {"verdict": "PASS"},
            {"verdict": "WARNING"},
        ]
    ) == "ACCEPTED_WITH_WARNINGS"
