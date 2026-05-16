from __future__ import annotations

from copy import deepcopy

from review.post_reprocess_review_decisions import validate_human_review_decisions


def _queue_payload() -> dict:
    return {
        "schema_version": "post_reprocess_review_queue_after_real_enrichment_v1",
        "source_prd": "PRD-046.0.9-RUN1",
        "items": [
            {"review_item_id": "post_reprocess::b1", "block_id": "b1"},
            {"review_item_id": "post_reprocess::b2", "block_id": "b2"},
        ],
    }


def _blocks_payload() -> dict:
    return {
        "schema_version": "bot_data_base_v1.0",
        "blocks": [
            {"id": "b1", "metadata": {"source_id": "123__кузница_духа", "governance": {}}},
            {"id": "b2", "metadata": {"source_id": "123__кузница_духа", "governance": {}}},
        ],
    }


def _base_decisions_payload() -> dict:
    return {
        "schema_version": "kb_review_decisions_v1",
        "source_prd": "PRD-046.0.9.1",
        "decisions": [],
    }


def test_empty_template_valid() -> None:
    result = validate_human_review_decisions(
        queue_payload=_queue_payload(),
        decisions_payload=_base_decisions_payload(),
        blocks_payload=_blocks_payload(),
        source_prd="PRD-046.0.9.1",
    )
    assert result["valid"] is True
    assert result["decisions_count"] == 0


def test_valid_approved_decision_passes() -> None:
    payload = _base_decisions_payload()
    payload["decisions"] = [
        {
            "review_item_id": "post_reprocess::b1",
            "block_id": "b1",
            "decision": "approved",
            "reviewer": "human",
            "reason": "",
            "approved_fields": ["summary", "tags"],
            "rejected_fields": [],
            "edited_fields": {},
            "source_prd": "PRD-046.0.9.1",
        }
    ]
    result = validate_human_review_decisions(
        queue_payload=_queue_payload(),
        decisions_payload=payload,
        blocks_payload=_blocks_payload(),
        source_prd="PRD-046.0.9.1",
    )
    assert result["valid"] is True


def test_valid_needs_edit_decision_passes() -> None:
    payload = _base_decisions_payload()
    payload["decisions"] = [
        {
            "review_item_id": "post_reprocess::b1",
            "block_id": "b1",
            "decision": "needs_edit",
            "reviewer": "admin",
            "reason": "fix avoid_when",
            "approved_fields": [],
            "rejected_fields": ["avoid_when"],
            "edited_fields": {"avoid_when": ["safer wording"]},
            "source_prd": "PRD-046.0.9.1",
        }
    ]
    result = validate_human_review_decisions(
        queue_payload=_queue_payload(),
        decisions_payload=payload,
        blocks_payload=_blocks_payload(),
        source_prd="PRD-046.0.9.1",
    )
    assert result["valid"] is True


def test_unknown_review_item_id_fails() -> None:
    payload = _base_decisions_payload()
    payload["decisions"] = [
        {
            "review_item_id": "post_reprocess::unknown",
            "block_id": "b1",
            "decision": "approved",
            "reviewer": "human",
            "reason": "",
            "approved_fields": ["summary"],
            "rejected_fields": [],
            "edited_fields": {},
            "source_prd": "PRD-046.0.9.1",
        }
    ]
    result = validate_human_review_decisions(
        queue_payload=_queue_payload(),
        decisions_payload=payload,
        blocks_payload=_blocks_payload(),
        source_prd="PRD-046.0.9.1",
    )
    assert result["valid"] is False
    assert "post_reprocess::unknown" in result["unknown_review_item_ids"]


def test_block_id_mismatch_fails() -> None:
    payload = _base_decisions_payload()
    payload["decisions"] = [
        {
            "review_item_id": "post_reprocess::b1",
            "block_id": "b2",
            "decision": "approved",
            "reviewer": "human",
            "reason": "",
            "approved_fields": ["summary"],
            "rejected_fields": [],
            "edited_fields": {},
            "source_prd": "PRD-046.0.9.1",
        }
    ]
    result = validate_human_review_decisions(
        queue_payload=_queue_payload(),
        decisions_payload=payload,
        blocks_payload=_blocks_payload(),
        source_prd="PRD-046.0.9.1",
    )
    assert result["valid"] is False
    assert "post_reprocess::b1" in result["block_id_mismatches"]


def test_duplicate_review_item_id_fails() -> None:
    payload = _base_decisions_payload()
    payload["decisions"] = [
        {
            "review_item_id": "post_reprocess::b1",
            "block_id": "b1",
            "decision": "approved",
            "reviewer": "human",
            "reason": "",
            "approved_fields": ["summary"],
            "rejected_fields": [],
            "edited_fields": {},
            "source_prd": "PRD-046.0.9.1",
        },
        {
            "review_item_id": "post_reprocess::b1",
            "block_id": "b1",
            "decision": "defer",
            "reviewer": "human",
            "reason": "need second pass",
            "approved_fields": [],
            "rejected_fields": [],
            "edited_fields": {},
            "source_prd": "PRD-046.0.9.1",
        },
    ]
    result = validate_human_review_decisions(
        queue_payload=_queue_payload(),
        decisions_payload=payload,
        blocks_payload=_blocks_payload(),
        source_prd="PRD-046.0.9.1",
    )
    assert result["valid"] is False
    assert "post_reprocess::b1" in result["duplicate_review_item_ids"]


def test_forbidden_edited_field_fails() -> None:
    payload = _base_decisions_payload()
    payload["decisions"] = [
        {
            "review_item_id": "post_reprocess::b1",
            "block_id": "b1",
            "decision": "needs_edit",
            "reviewer": "human",
            "reason": "bad field",
            "approved_fields": [],
            "rejected_fields": [],
            "edited_fields": {"allowed_use": ["writer_context"]},
            "source_prd": "PRD-046.0.9.1",
        }
    ]
    result = validate_human_review_decisions(
        queue_payload=_queue_payload(),
        decisions_payload=payload,
        blocks_payload=_blocks_payload(),
        source_prd="PRD-046.0.9.1",
    )
    assert result["valid"] is False
    assert result["authority_field_mutation_attempts"]


def test_raw_text_key_fails() -> None:
    payload = _base_decisions_payload()
    payload["raw_text"] = "should_not_be_here"
    result = validate_human_review_decisions(
        queue_payload=_queue_payload(),
        decisions_payload=payload,
        blocks_payload=_blocks_payload(),
        source_prd="PRD-046.0.9.1",
    )
    assert result["valid"] is False
    assert "forbidden_keys_present" in result["errors"]


def test_secret_like_value_fails() -> None:
    payload = _base_decisions_payload()
    payload["decisions"] = [
        {
            "review_item_id": "post_reprocess::b1",
            "block_id": "b1",
            "decision": "needs_edit",
            "reviewer": "human",
            "reason": "token=abc",
            "approved_fields": [],
            "rejected_fields": ["summary"],
            "edited_fields": {"summary": "safe"},
            "source_prd": "PRD-046.0.9.1",
        }
    ]
    result = validate_human_review_decisions(
        queue_payload=_queue_payload(),
        decisions_payload=payload,
        blocks_payload=_blocks_payload(),
        source_prd="PRD-046.0.9.1",
    )
    assert result["valid"] is False
    assert "secret_like_values_present" in result["errors"]


def test_needs_edit_without_changes_fails() -> None:
    payload = _base_decisions_payload()
    payload["decisions"] = [
        {
            "review_item_id": "post_reprocess::b1",
            "block_id": "b1",
            "decision": "needs_edit",
            "reviewer": "admin",
            "reason": "missing edited fields",
            "approved_fields": [],
            "rejected_fields": [],
            "edited_fields": {},
            "source_prd": "PRD-046.0.9.1",
        }
    ]
    result = validate_human_review_decisions(
        queue_payload=_queue_payload(),
        decisions_payload=payload,
        blocks_payload=_blocks_payload(),
        source_prd="PRD-046.0.9.1",
    )
    assert result["valid"] is False
    assert any("needs_edit_without_changes" in item for item in result["errors"])


def test_approved_with_edited_fields_fails() -> None:
    payload = _base_decisions_payload()
    payload["decisions"] = [
        {
            "review_item_id": "post_reprocess::b1",
            "block_id": "b1",
            "decision": "approved",
            "reviewer": "human",
            "reason": "",
            "approved_fields": ["summary"],
            "rejected_fields": [],
            "edited_fields": {"summary": "edited"},
            "source_prd": "PRD-046.0.9.1",
        }
    ]
    result = validate_human_review_decisions(
        queue_payload=_queue_payload(),
        decisions_payload=payload,
        blocks_payload=_blocks_payload(),
        source_prd="PRD-046.0.9.1",
    )
    assert result["valid"] is False
    assert any("approved_must_not_have_edited_fields" in item for item in result["errors"])


def test_block_id_missing_in_blocks_fails() -> None:
    blocks_payload = _blocks_payload()
    blocks_payload["blocks"] = [blocks_payload["blocks"][0]]
    payload = _base_decisions_payload()
    payload["decisions"] = [
        {
            "review_item_id": "post_reprocess::b2",
            "block_id": "b2",
            "decision": "approved",
            "reviewer": "human",
            "reason": "",
            "approved_fields": ["summary"],
            "rejected_fields": [],
            "edited_fields": {},
            "source_prd": "PRD-046.0.9.1",
        }
    ]
    result = validate_human_review_decisions(
        queue_payload=_queue_payload(),
        decisions_payload=payload,
        blocks_payload=blocks_payload,
        source_prd="PRD-046.0.9.1",
    )
    assert result["valid"] is False
    assert any("block_id_missing_in_blocks" in item for item in result["errors"])


def test_schema_mismatch_fails() -> None:
    payload = deepcopy(_base_decisions_payload())
    payload["schema_version"] = "wrong_schema"
    result = validate_human_review_decisions(
        queue_payload=_queue_payload(),
        decisions_payload=payload,
        blocks_payload=_blocks_payload(),
        source_prd="PRD-046.0.9.1",
    )
    assert result["valid"] is False
    assert "schema_version_mismatch" in result["errors"]
