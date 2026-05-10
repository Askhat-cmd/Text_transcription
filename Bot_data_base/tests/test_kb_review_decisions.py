from __future__ import annotations

from review.review_decision_validator import validate_decisions_overlay


def _queue_payload() -> dict:
    return {
        "schema_version": "kb_review_queue_v1",
        "source_prd": "PRD-046.0.7",
        "generated_at": "2026-01-01T00:00:00+00:00",
        "items": [
            {"review_item_id": "kbri_1", "block_id": "b1"},
            {"review_item_id": "kbri_2", "block_id": "b2"},
        ],
    }


def test_valid_empty_template_passes() -> None:
    result = validate_decisions_overlay(
        queue_payload=_queue_payload(),
        decisions_payload={"schema_version": "kb_review_decisions_v1", "decisions": []},
        source_prd="PRD-046.0.7",
    )
    assert result["valid"] is True
    assert result["decisions_count"] == 0


def test_valid_decision_fixture_passes() -> None:
    decisions = {
        "schema_version": "kb_review_decisions_v1",
        "decisions": [
            {
                "review_item_id": "kbri_1",
                "block_id": "b1",
                "decision": "approved",
                "reviewer": "human",
                "reason": "",
                "approved_fields": ["summary", "tags"],
                "rejected_fields": [],
                "edited_fields": {},
                "created_at": "2026-01-01T00:00:00+00:00",
                "source_prd": "PRD-046.0.7",
            },
            {
                "review_item_id": "kbri_2",
                "block_id": "b2",
                "decision": "needs_edit",
                "reviewer": "admin",
                "reason": "fix avoid_when",
                "approved_fields": [],
                "rejected_fields": ["avoid_when"],
                "edited_fields": {"avoid_when": ["x"]},
                "created_at": "2026-01-01T00:00:00+00:00",
                "source_prd": "PRD-046.0.7",
            },
        ],
    }
    result = validate_decisions_overlay(
        queue_payload=_queue_payload(),
        decisions_payload=decisions,
        source_prd="PRD-046.0.7",
    )
    assert result["valid"] is True


def test_unknown_review_item_id_fails() -> None:
    result = validate_decisions_overlay(
        queue_payload=_queue_payload(),
        decisions_payload={
            "schema_version": "kb_review_decisions_v1",
            "decisions": [
                {
                    "review_item_id": "kbri_unknown",
                    "block_id": "b1",
                    "decision": "approved",
                    "reviewer": "human",
                    "reason": "",
                    "approved_fields": ["summary"],
                    "rejected_fields": [],
                    "edited_fields": {},
                    "source_prd": "PRD-046.0.7",
                }
            ],
        },
        source_prd="PRD-046.0.7",
    )
    assert result["valid"] is False
    assert result["unknown_review_item_ids"] == ["kbri_unknown"]


def test_invalid_decision_enum_fails() -> None:
    result = validate_decisions_overlay(
        queue_payload=_queue_payload(),
        decisions_payload={
            "schema_version": "kb_review_decisions_v1",
            "decisions": [
                {
                    "review_item_id": "kbri_1",
                    "block_id": "b1",
                    "decision": "bad_enum",
                    "reviewer": "human",
                    "reason": "",
                    "approved_fields": ["summary"],
                    "rejected_fields": [],
                    "edited_fields": {},
                    "source_prd": "PRD-046.0.7",
                }
            ],
        },
        source_prd="PRD-046.0.7",
    )
    assert result["valid"] is False
    assert any("invalid_decision" in item for item in result["errors"])


def test_forbidden_field_in_edited_fields_fails() -> None:
    result = validate_decisions_overlay(
        queue_payload=_queue_payload(),
        decisions_payload={
            "schema_version": "kb_review_decisions_v1",
            "decisions": [
                {
                    "review_item_id": "kbri_1",
                    "block_id": "b1",
                    "decision": "needs_edit",
                    "reviewer": "human",
                    "reason": "unsafe",
                    "approved_fields": [],
                    "rejected_fields": [],
                    "edited_fields": {"allowed_use": ["writer_context"]},
                    "source_prd": "PRD-046.0.7",
                }
            ],
        },
        source_prd="PRD-046.0.7",
    )
    assert result["valid"] is False
    assert any("edited_field_not_allowed:allowed_use" in item for item in result["errors"])


def test_raw_text_key_fails() -> None:
    result = validate_decisions_overlay(
        queue_payload=_queue_payload(),
        decisions_payload={"schema_version": "kb_review_decisions_v1", "decisions": [], "raw_text": "bad"},
        source_prd="PRD-046.0.7",
    )
    assert result["valid"] is False
    assert "forbidden_keys_present" in result["errors"]


def test_secret_like_value_fails() -> None:
    result = validate_decisions_overlay(
        queue_payload=_queue_payload(),
        decisions_payload={
            "schema_version": "kb_review_decisions_v1",
            "decisions": [
                {
                    "review_item_id": "kbri_1",
                    "block_id": "b1",
                    "decision": "needs_edit",
                    "reviewer": "human",
                    "reason": "token=abc",
                    "approved_fields": [],
                    "rejected_fields": [],
                    "edited_fields": {},
                    "source_prd": "PRD-046.0.7",
                }
            ],
        },
        source_prd="PRD-046.0.7",
    )
    assert result["valid"] is False
    assert "secret_like_values_present" in result["errors"]


def test_block_id_mismatch_fails() -> None:
    result = validate_decisions_overlay(
        queue_payload=_queue_payload(),
        decisions_payload={
            "schema_version": "kb_review_decisions_v1",
            "decisions": [
                {
                    "review_item_id": "kbri_1",
                    "block_id": "wrong",
                    "decision": "approved",
                    "reviewer": "human",
                    "reason": "",
                    "approved_fields": ["summary"],
                    "rejected_fields": [],
                    "edited_fields": {},
                    "source_prd": "PRD-046.0.7",
                }
            ],
        },
        source_prd="PRD-046.0.7",
    )
    assert result["valid"] is False
    assert any("block_id_mismatch:kbri_1" in item for item in result["errors"])

