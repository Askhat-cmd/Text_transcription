from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = ROOT / "TO_DO_LIST" / "logs" / "PRD-047.15-HF1"
REQUIRED_FIELDS = {
    "case_id",
    "user_message",
    "last_assistant_offer",
    "dialogue_act",
    "answer_obligation",
    "summary_request",
    "composer.version",
    "composer.mode",
    "composer.retrieval_need",
    "composer.retrieval_action",
    "composer.query_source",
    "composer.composed_query",
    "composer.query_terms",
    "composer.inherited_topic",
    "composer.inherited_offer_type",
    "composer.confidence",
    "composer.writer_can_ignore_rag",
    "composer.include_for_writer_if_found",
    "composer.reason",
    "composer.evidence",
    "composer.no_user_facing_text_created",
    "expected_category",
    "computed_category",
    "review_flags",
}


def _read_json(name: str):
    return json.loads((LOG_DIR / name).read_text(encoding="utf-8-sig"))


def test_trace_schema_contains_required_fields() -> None:
    schema = _read_json("composer_trace_schema.json")

    assert REQUIRED_FIELDS.issubset(set(schema["required_fields"]))
    assert schema["runtime_behavior_mutation"] is False
    assert schema["llm_calls_allowed"] is False
    assert schema["no_user_facing_text_created_required"] is True


def test_case_library_has_at_least_40_expected_cases() -> None:
    cases = _read_json("composer_calibration_cases.json")

    assert len(cases) >= 40
    groups = {case["group"] for case in cases}
    assert {
        "short_contextual_followup",
        "summary_request",
        "knowledge_question",
        "mixed_context",
        "noise_suppression",
    }.issubset(groups)
    for case in cases:
        assert case.get("case_id")
        assert case.get("user_message")
        assert case.get("expected_category")
        assert case.get("expected_retrieval_actions")


def test_trace_results_have_required_fields_and_no_stub_text() -> None:
    result = _read_json("composer_trace_review_results.json")

    assert result["metrics"]["cases_total"] >= 40
    assert result["metrics"]["literal_short_reply_query_count"] == 0
    assert result["metrics"]["summary_external_kb_leak_count"] == 0
    assert result["metrics"]["no_stub_violations_count"] == 0
    for trace in result["traces"]:
        assert trace["case_id"]
        assert "composer" in trace
        composer = trace["composer"]
        assert composer["version"] == "contextual_retrieval_query_composer_v1"
        assert composer["mode"] == "deterministic_v1"
        assert composer["no_user_facing_text_created"] is True
        assert isinstance(trace["review_flags"], dict)
