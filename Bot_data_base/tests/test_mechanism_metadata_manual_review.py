from __future__ import annotations

from pathlib import Path

from knowledge_governance.manual_review import (
    build_candidate_index,
    build_curated_overlay_preview,
    build_review_decisions_template,
    build_review_queue,
    validate_review_decisions,
)
from knowledge_governance.offline_enrichment import read_json
from tools.run_mechanism_metadata_review import build_fixture_decisions


REPO_ROOT = Path(__file__).resolve().parents[2]
PRD17_LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.17"


def _candidate_run() -> dict:
    return read_json(PRD17_LOG_DIR / "enrichment_candidates_deterministic.json")


def _manual_pack() -> dict:
    return read_json(PRD17_LOG_DIR / "manual_review_pack.json")


def _find_candidate(*, chunk_type: str, risk_level: str | None = None) -> dict:
    for candidate in _candidate_run()["candidates"]:
        current_chunk = ((candidate.get("current_metadata_summary") or {}).get("chunk_type") or "").lower()
        current_risk = ((candidate.get("governance_review") or {}).get("risk_level") or "").lower()
        if current_chunk != chunk_type:
            continue
        if risk_level is not None and current_risk != risk_level:
            continue
        return candidate
    raise AssertionError(f"candidate not found: {chunk_type=} {risk_level=}")


def test_pending_template_validation_passes_with_no_accepted_fields() -> None:
    candidate = _find_candidate(chunk_type="concept", risk_level="low")
    document = build_review_decisions_template([candidate])
    report = validate_review_decisions(document, build_candidate_index([candidate]))
    assert report["status"] == "passed_with_no_accepted_fields"
    assert report["accepted_item_count"] == 0
    assert report["accepted_field_count"] == 0


def test_invalid_schema_and_missing_candidate_id_fail() -> None:
    candidate = _find_candidate(chunk_type="concept", risk_level="low")
    document = build_review_decisions_template([candidate])
    document["schema_version"] = "broken"
    document["decisions"][0]["schema_version"] = "broken"
    document["decisions"][0]["candidate_id"] = ""
    report = validate_review_decisions(document, build_candidate_index([candidate]))
    assert report["status"] == "failed"
    assert "invalid_document_schema_version" in report["errors"]
    assert "invalid_schema_version" in report["errors"]
    assert "missing_candidate_id" in report["errors"]


def test_accepted_empty_value_and_safe_to_apply_true_fail() -> None:
    candidate = _find_candidate(chunk_type="concept", risk_level="low")
    document = build_review_decisions_template([candidate])
    decision = document["decisions"][0]
    decision["review_status"] = "accepted"
    decision["reviewer_role"] = "fixture_only"
    decision["reviewer_id"] = "x"
    decision["reviewed_at"] = "2026-06-16T00:00:00+00:00"
    decision["safe_to_apply_to_live_metadata"] = True
    decision["field_decisions"]["summary_candidate"]["decision"] = "accept"
    decision["field_decisions"]["summary_candidate"]["value"] = ""
    report = validate_review_decisions(document, build_candidate_index([candidate]))
    assert "safe_to_apply_to_live_metadata_must_be_false" in report["errors"]
    assert "summary_candidate:accepted_value_empty" in report["errors"]


def test_invalid_depth_quote_and_chunk_type_fail() -> None:
    candidate = _find_candidate(chunk_type="concept", risk_level="low")
    document = build_review_decisions_template([candidate])
    decision = document["decisions"][0]
    decision["review_status"] = "accepted_with_edits"
    decision["reviewer_role"] = "fixture_only"
    decision["reviewer_id"] = "x"
    decision["reviewed_at"] = "2026-06-16T00:00:00+00:00"
    for field_name, value in {
        "depth_level_suggestion": 7,
        "quote_policy_suggestion": "bad_policy",
        "chunk_type_review_suggestion": "bad_chunk",
    }.items():
        decision["field_decisions"][field_name]["decision"] = "accept_with_edit"
        decision["field_decisions"][field_name]["value"] = value
    report = validate_review_decisions(document, build_candidate_index([candidate]))
    assert "depth_level_suggestion_out_of_range" in report["errors"]
    assert "quote_policy_suggestion_out_of_vocab" in report["errors"]
    assert "chunk_type_review_suggestion_out_of_vocab" in report["errors"]


def test_high_risk_practice_acceptance_requires_contraindications_and_avoid_when() -> None:
    candidate = _find_candidate(chunk_type="practice", risk_level="high")
    document = build_review_decisions_template([candidate])
    decision = document["decisions"][0]
    decision["review_status"] = "accepted"
    decision["reviewer_role"] = "fixture_only"
    decision["reviewer_id"] = "x"
    decision["reviewed_at"] = "2026-06-16T00:00:00+00:00"
    decision["field_decisions"]["allowed_writer_use_candidate"]["decision"] = "accept"
    decision["field_decisions"]["allowed_writer_use_candidate"]["value"] = (
        candidate["candidate_fields"]["allowed_writer_use_candidate"]
    )
    report = validate_review_decisions(document, build_candidate_index([candidate]))
    assert "accepted_practice_requires_contraindications_decision" in report["errors"]
    assert "accepted_practice_requires_avoid_when_decision" in report["errors"]
    assert "high_risk_practice_missing_accepted_contraindications" in report["errors"]


def test_deferred_high_risk_practice_passes() -> None:
    candidate = _find_candidate(chunk_type="practice", risk_level="high")
    document = build_review_decisions_template([candidate])
    decision = document["decisions"][0]
    decision["review_status"] = "deferred"
    decision["reviewer_role"] = "fixture_only"
    decision["reviewer_id"] = "x"
    decision["reviewed_at"] = "2026-06-16T00:00:00+00:00"
    report = validate_review_decisions(document, build_candidate_index([candidate]))
    assert report["status"] == "passed_with_no_accepted_fields"


def test_review_queue_contains_all_candidates_with_priority_and_truncated_previews() -> None:
    queue_document = build_review_queue(candidate_run=_candidate_run(), manual_review_pack=_manual_pack())
    assert queue_document["queue_count"] == 80
    assert queue_document["candidate_count"] == 80
    assert queue_document["items"][0]["queue_priority"].startswith("P1_")
    assert all(len(item["content_preview"]) <= 300 for item in queue_document["items"])


def test_source_fragment_queue_recommends_derived_review() -> None:
    queue_document = build_review_queue(candidate_run=_candidate_run(), manual_review_pack=_manual_pack())
    source_fragment_item = next(item for item in queue_document["items"] if item["chunk_type"] == "source_fragment")
    assert "derived candidate" in source_fragment_item["recommended_reviewer_action"]


def test_fixture_overlay_includes_only_accepted_items() -> None:
    fixture_document, _ = build_fixture_decisions()
    candidate_index = build_candidate_index(_candidate_run()["candidates"])
    overlay = build_curated_overlay_preview(candidate_index=candidate_index, decision_document=fixture_document)
    included_ids = {item["candidate_id"] for item in overlay["items"]}
    rejected_id = fixture_document["decisions"][1]["candidate_id"]
    deferred_id = fixture_document["decisions"][2]["candidate_id"]
    assert overlay["live_apply_allowed"] is False
    assert overlay["summary"]["accepted_item_count"] >= 2
    assert rejected_id not in included_ids
    assert deferred_id not in included_ids
