from __future__ import annotations

from review.controlled_review_decision_apply import (
    build_apply_plan,
    validate_apply_plan,
)


def _block(block_id: str) -> dict:
    return {
        "id": block_id,
        "source": "book:123__кузница_духа",
        "text": f"text-{block_id}",
        "metadata": {
            "source_id": "123__кузница_духа",
            "governance": {
                "chunk_type": "theory",
                "allowed_use": ["writer_context"],
                "safety_flags": ["not_for_direct_quote"],
            }
        },
    }


def _queue_item(rid: str, block_id: str) -> dict:
    return {
        "review_item_id": rid,
        "block_id": block_id,
        "source_id": "123__кузница_духа",
        "chunk_type": "theory",
        "review_priority": "P2",
        "review_reasons": ["needs_human_review"],
    }


def test_apply_plan_routes_and_field_filters() -> None:
    blocks_payload = {"blocks": [_block("b1"), _block("b2"), _block("b3"), _block("b4"), _block("b5")]}
    queue_payload = {
        "source_prd": "PRD-046.0.9-RUN1",
        "items": [
            _queue_item("rid-1", "b1"),
            _queue_item("rid-2", "b2"),
            _queue_item("rid-3", "b3"),
            _queue_item("rid-4", "b4"),
        ],
    }
    decisions_payload = {
        "source_prd": "PRD-046.0.9.3",
        "decisions": [
            {"review_item_id": "rid-1", "block_id": "b1", "decision": "approved", "approved_fields": ["summary", "text", "tags"]},
            {
                "review_item_id": "rid-2",
                "block_id": "b2",
                "decision": "needs_edit",
                "edited_fields": {"summary": "edited", "tags": ["safe"], "governance": {"chunk_type": "quote"}},
            },
            {"review_item_id": "rid-3", "block_id": "b3", "decision": "rejected"},
            {"review_item_id": "rid-4", "block_id": "b4", "decision": "defer"},
        ],
    }
    run1_index = {
        "b1": {"summary": "sum-b1", "tags": ["t1"], "text": "forbidden"},
        "b2": {"summary": "sum-b2", "tags": ["t2"]},
        "b5": {"summary": "sum-b5", "tags": ["safe-non-review"]},
    }

    plan, actions = build_apply_plan(
        source_prd="PRD-046.0.7.1",
        blocks_payload=blocks_payload,
        queue_payload=queue_payload,
        decisions_payload=decisions_payload,
        run1_index=run1_index,
    )
    assert plan["total_blocks"] == 5
    assert plan["review_items_count"] == 4
    assert plan["review_approved_apply_candidates"] == 1
    assert plan["review_needs_edit_apply_candidates"] == 1
    assert plan["review_rejected_skip"] == 1
    assert plan["review_defer_skip"] == 1
    assert plan["safe_non_review_apply_candidates"] == 1

    by_route = {item["route"]: item for item in actions}
    approved = by_route["review_approved_apply"]
    assert approved["payload"] == {"summary": "sum-b1", "tags": ["t1"]}
    needs_edit = by_route["review_needs_edit_apply"]
    assert needs_edit["payload"] == {"summary": "edited", "tags": ["safe"]}
    safe_non_review = by_route["safe_non_review_apply"]
    assert safe_non_review["payload"]["summary"] == "sum-b5"
    assert "text" not in safe_non_review["payload"]

    validation = validate_apply_plan(
        plan=plan,
        actions=actions,
        expected_total_blocks=5,
        expected_review_items=4,
        expected_decisions_count=4,
    )
    assert validation["valid"] is True
    assert validation["errors"] == []


def test_validate_apply_plan_fails_on_forbidden_action_payload() -> None:
    plan = {
        "total_blocks": 1,
        "review_items_count": 1,
        "review_approved_apply_candidates": 1,
        "review_needs_edit_apply_candidates": 0,
        "safe_non_review_apply_candidates": 0,
        "expected_safe_non_review_candidates": 0,
        "max_expected_apply_candidates": 1,
        "actual_apply_candidates": 1,
        "authority_mutation_planned": False,
        "text_mutation_planned": False,
        "governance_mutation_planned": False,
        "duplicate_decision_ids": [],
        "plan_warnings": [],
    }
    actions = [{"route": "review_approved_apply", "payload": {"text": "forbidden"}}]
    validation = validate_apply_plan(
        plan=plan,
        actions=actions,
        expected_total_blocks=1,
        expected_review_items=1,
        expected_decisions_count=1,
    )
    assert validation["valid"] is False
    assert "authority_field_in_action_payload" in validation["errors"]
