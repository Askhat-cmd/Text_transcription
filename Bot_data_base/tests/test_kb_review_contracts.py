from __future__ import annotations

from review.review_contracts import (
    build_review_item_id,
    validate_review_decision_payload,
    validate_review_item_payload,
)
from review.review_sanitizer import (
    contains_forbidden_review_key,
    contains_secret_like_value,
    find_forbidden_review_keys,
    sanitize_preview,
)


def test_review_item_id_is_deterministic() -> None:
    first = build_review_item_id("source_a", "block_1", "kb_llm_enrichment_v1")
    second = build_review_item_id("source_a", "block_1", "kb_llm_enrichment_v1")
    assert first == second
    assert first.startswith("kbri_")


def test_sanitize_preview_max_length() -> None:
    value = sanitize_preview("x" * 500, limit=240)
    assert len(value) <= 240


def test_forbidden_keys_detected_recursively() -> None:
    payload = {"a": {"b": [{"content_full": "secret"}]}}
    hits = find_forbidden_review_keys(payload)
    assert hits
    assert contains_forbidden_review_key(payload) is True


def test_secret_like_value_detected() -> None:
    assert contains_secret_like_value("OPENAI_API_KEY=sk-123")
    assert contains_secret_like_value("token=abcd")
    assert contains_secret_like_value(".env")


def test_invalid_review_item_enum_fails() -> None:
    errors = validate_review_item_payload(
        {
            "review_item_id": "kbri_x",
            "block_id": "b1",
            "source_id": "s1",
            "source_title": "title",
            "chunk_type": "invalid",
            "review_priority": "P1",
            "recommended_action": "needs_edit",
            "content_preview": "ok",
            "source_prd": "PRD-046.0.7",
        }
    )
    assert "invalid_chunk_type" in errors


def test_allowed_advisory_fields_pass() -> None:
    errors = validate_review_decision_payload(
        {
            "review_item_id": "kbri_x",
            "block_id": "b1",
            "decision": "needs_edit",
            "reviewer": "human",
            "reason": "fix summary",
            "approved_fields": ["summary"],
            "rejected_fields": ["avoid_when"],
            "edited_fields": {"summary": "edited"},
            "source_prd": "PRD-046.0.7",
        }
    )
    assert errors == []


def test_governance_authority_field_in_edited_fields_fails() -> None:
    errors = validate_review_decision_payload(
        {
            "review_item_id": "kbri_x",
            "block_id": "b1",
            "decision": "needs_edit",
            "reviewer": "human",
            "reason": "bad",
            "approved_fields": [],
            "rejected_fields": [],
            "edited_fields": {"allowed_use": ["writer_context"]},
            "source_prd": "PRD-046.0.7",
        }
    )
    assert any(item.startswith("edited_field_not_allowed:allowed_use") for item in errors)

