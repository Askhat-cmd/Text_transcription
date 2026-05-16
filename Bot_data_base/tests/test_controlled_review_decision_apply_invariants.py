from __future__ import annotations

from review.controlled_review_decision_apply import (
    apply_actions_to_blocks,
    build_preflight_report,
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


def test_apply_actions_preserves_authority_fields() -> None:
    blocks_payload = {"blocks": [_block("b1"), _block("b2")]}
    actions = [
        {"block_id": "b1", "route": "review_approved_apply", "payload": {"summary": "sum-1", "tags": ["x"]}},
        {"block_id": "b2", "route": "safe_non_review_apply", "payload": {"summary": "sum-2"}},
    ]
    updated, summary = apply_actions_to_blocks(blocks_payload=blocks_payload, actions=actions)
    assert summary["updated_blocks"] == 2
    assert summary["text_changed_count"] == 0
    assert summary["chunk_type_changed_count"] == 0
    assert summary["allowed_use_changed_count"] == 0
    assert summary["safety_flags_changed_count"] == 0
    assert summary["source_id_changed_count"] == 0
    assert summary["block_id_changed_count"] == 0
    assert summary["governance_invariant_violations"] == 0
    llm = updated["blocks"][0]["metadata"]["llm_enrichment"]
    assert llm["summary"] == "sum-1"


def test_preflight_fails_closed_without_authoritative_run1() -> None:
    blocks_payload = {"blocks": [_block("b1")]}
    queue_payload = {"source_prd": "PRD-046.0.9-RUN1", "items": [{"review_item_id": "rid-1", "block_id": "b1"}]}
    decisions_payload = {
        "schema_version": "kb_review_decisions_v1",
        "source_prd": "PRD-046.0.9.3",
        "decision_owner": "architect_auto_policy",
        "apply_ready": True,
        "decisions": [
            {
                "review_item_id": "rid-1",
                "block_id": "b1",
                "decision": "approved",
                "reviewer": "policy_auto",
                "reason": "",
                "approved_fields": ["summary"],
                "rejected_fields": [],
                "edited_fields": {},
                "created_at": "2026-05-16T00:00:00+00:00",
                "source_prd": "PRD-046.0.9.3",
            }
        ],
    }
    report = build_preflight_report(
        source_prd="PRD-046.0.7.1",
        blocks_payload=blocks_payload,
        queue_payload=queue_payload,
        decisions_payload=decisions_payload,
        overlays_equal=True,
        run1_candidates=[],
        run1_discovery_warnings=[],
        expected_blocks_total=1,
        expected_review_items=1,
        expected_decisions_count=1,
        expected_queue_source_prd="PRD-046.0.9-RUN1",
    )
    assert report["preflight_passed"] is False
    assert "authoritative_run1_enrichment_not_unique" in report["blockers"]


def test_preflight_flags_unknown_review_item_and_duplicate_ids() -> None:
    blocks_payload = {"blocks": [_block("b1"), _block("b2")]}
    queue_payload = {"source_prd": "PRD-046.0.9-RUN1", "items": [{"review_item_id": "rid-1", "block_id": "b1"}]}
    decisions_payload = {
        "schema_version": "kb_review_decisions_v1",
        "source_prd": "PRD-046.0.9.3",
        "decision_owner": "architect_auto_policy",
        "apply_ready": True,
        "decisions": [
            {
                "review_item_id": "rid-unknown",
                "block_id": "b2",
                "decision": "approved",
                "reviewer": "policy_auto",
                "reason": "",
                "approved_fields": ["summary"],
                "rejected_fields": [],
                "edited_fields": {},
                "created_at": "2026-05-16T00:00:00+00:00",
                "source_prd": "PRD-046.0.9.3",
            },
            {
                "review_item_id": "rid-unknown",
                "block_id": "b2",
                "decision": "approved",
                "reviewer": "policy_auto",
                "reason": "",
                "approved_fields": ["summary"],
                "rejected_fields": [],
                "edited_fields": {},
                "created_at": "2026-05-16T00:00:01+00:00",
                "source_prd": "PRD-046.0.9.3",
            },
        ],
    }
    report = build_preflight_report(
        source_prd="PRD-046.0.7.1",
        blocks_payload=blocks_payload,
        queue_payload=queue_payload,
        decisions_payload=decisions_payload,
        overlays_equal=True,
        run1_candidates=[{"overlay_path": "x", "validation_path": "y"}],
        run1_discovery_warnings=[],
        expected_blocks_total=2,
        expected_review_items=1,
        expected_decisions_count=2,
        expected_queue_source_prd="PRD-046.0.9-RUN1",
    )
    assert report["preflight_passed"] is False
    blockers = set(report["blockers"])
    assert "overlay_duplicate_review_item_ids_not_empty" in blockers
    assert "overlay_unknown_review_item_ids_not_empty" in blockers


def test_plan_validation_blocks_explicit_authority_mutation_flag() -> None:
    validation = validate_apply_plan(
        plan={
            "total_blocks": 1,
            "review_items_count": 1,
            "review_approved_apply_candidates": 0,
            "review_needs_edit_apply_candidates": 0,
            "safe_non_review_apply_candidates": 0,
            "expected_safe_non_review_candidates": 0,
            "max_expected_apply_candidates": 0,
            "actual_apply_candidates": 0,
            "authority_mutation_planned": True,
            "text_mutation_planned": False,
            "governance_mutation_planned": False,
            "duplicate_decision_ids": [],
            "plan_warnings": [],
        },
        actions=[],
        expected_total_blocks=1,
        expected_review_items=1,
        expected_decisions_count=1,
    )
    assert validation["valid"] is False
    assert "unallowed_mutation_planned" in validation["errors"]
