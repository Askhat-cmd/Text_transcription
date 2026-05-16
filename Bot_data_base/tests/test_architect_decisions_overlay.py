from __future__ import annotations

from review.architect_review_pass import validate_architect_decisions_overlay


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
        "source_prd": "PRD-046.0.9.2",
        "decision_owner": "architect_chatgpt",
        "decisions": [],
    }


def test_empty_overlay_ready_for_architect_review() -> None:
    result = validate_architect_decisions_overlay(
        queue_payload=_queue_payload(),
        decisions_payload=_base_decisions_payload(),
        blocks_payload=_blocks_payload(),
        source_prd="PRD-046.0.9.2",
    )
    assert result["valid"] is True
    assert result["coverage"]["queue_items_count"] == 2
    assert result["coverage"]["decisions_count"] == 0
    assert result["ready_for_architect_review"] is True
    assert result["apply_ready"] is False


def test_full_overlay_apply_ready_true() -> None:
    payload = _base_decisions_payload()
    payload["decisions"] = [
        {
            "review_item_id": "post_reprocess::b1",
            "block_id": "b1",
            "decision": "approved",
            "reviewer": "architect",
            "reason": "",
            "approved_fields": ["summary", "tags"],
            "rejected_fields": [],
            "edited_fields": {},
            "source_prd": "PRD-046.0.9.2",
        },
        {
            "review_item_id": "post_reprocess::b2",
            "block_id": "b2",
            "decision": "needs_edit",
            "reviewer": "architect",
            "reason": "tighten avoid_when",
            "approved_fields": [],
            "rejected_fields": ["avoid_when"],
            "edited_fields": {"avoid_when": ["safer framing"]},
            "source_prd": "PRD-046.0.9.2",
        },
    ]
    result = validate_architect_decisions_overlay(
        queue_payload=_queue_payload(),
        decisions_payload=payload,
        blocks_payload=_blocks_payload(),
        source_prd="PRD-046.0.9.2",
    )
    assert result["valid"] is True
    assert result["coverage"]["unique_review_item_ids_count"] == 2
    assert result["coverage"]["remaining_items_count"] == 0
    assert result["ready_for_architect_review"] is False
    assert result["apply_ready"] is True


def test_invalid_decision_value_detected() -> None:
    payload = _base_decisions_payload()
    payload["decisions"] = [
        {
            "review_item_id": "post_reprocess::b1",
            "block_id": "b1",
            "decision": "auto_approve",
            "reviewer": "architect",
            "reason": "",
            "approved_fields": ["summary"],
            "rejected_fields": [],
            "edited_fields": {},
            "source_prd": "PRD-046.0.9.2",
        }
    ]
    result = validate_architect_decisions_overlay(
        queue_payload=_queue_payload(),
        decisions_payload=payload,
        blocks_payload=_blocks_payload(),
        source_prd="PRD-046.0.9.2",
    )
    assert result["valid"] is False
    assert "auto_approve" in result["invalid_decision_values"]
    assert result["apply_ready"] is False
