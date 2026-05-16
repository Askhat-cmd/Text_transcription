from __future__ import annotations

from review.post_apply_quality_gate import build_apply_route_consistency


def _block(block_id: str, llm: dict | None = None) -> dict:
    return {
        "id": block_id,
        "source": "book:123__кузница_духа",
        "metadata": {
            "source_id": "123__кузница_духа",
            "governance": {"chunk_type": "theory", "allowed_use": ["writer_context"], "safety_flags": ["not_for_direct_quote"]},
            "llm_enrichment": llm or {},
        },
    }


def test_apply_routes_pass_expected_counts() -> None:
    blocks_payload = {
        "blocks": [
            _block("b1", {"summary": "s1", "applied_by_prd": "PRD-046.0.7.1", "apply_route": "review_approved_apply"}),
            _block("b2", {"summary": "s2", "apply_route": "review_needs_edit_apply"}),
            _block("b3", {"summary": "s3", "apply_route": "safe_non_review_apply"}),
        ]
    }
    apply_result = {
        "plan": {
            "safe_non_review_apply_candidates": 160,
            "review_approved_apply_candidates": 28,
            "review_needs_edit_apply_candidates": 12,
            "review_rejected_skip": 1,
            "review_defer_skip": 46,
        },
        "apply_summary": {
            "updated_blocks": 200,
            "applied_route_counts": {
                "safe_non_review_apply": 160,
                "review_approved_apply": 28,
                "review_needs_edit_apply": 12,
            },
        },
    }
    decisions_overlay = {"decisions": [{"decision": "approved"}] * 28 + [{"decision": "needs_edit"}] * 12 + [{"decision": "rejected"}] + [{"decision": "defer"}] * 46}
    review_queue = {"items": [{} for _ in range(87)]}
    gate = build_apply_route_consistency(
        blocks_payload=blocks_payload,
        apply_result_payload=apply_result,
        decisions_overlay_payload=decisions_overlay,
        review_queue_payload=review_queue,
    )
    assert gate["apply_route_consistency_passed"] is True
    assert gate["rejected_applied_count"] == 0
    assert gate["defer_applied_count"] == 0


def test_apply_routes_fail_on_rejected_or_defer_applied() -> None:
    blocks_payload = {"blocks": [_block("b1", {"summary": "x", "apply_route": "review_rejected_apply"})]}
    apply_result = {
        "plan": {
            "safe_non_review_apply_candidates": 160,
            "review_approved_apply_candidates": 28,
            "review_needs_edit_apply_candidates": 12,
            "review_rejected_skip": 1,
            "review_defer_skip": 46,
        },
        "apply_summary": {
            "updated_blocks": 200,
            "applied_route_counts": {
                "safe_non_review_apply": 160,
                "review_approved_apply": 28,
                "review_needs_edit_apply": 12,
                "review_rejected_apply": 1,
            },
        },
    }
    decisions_overlay = {"decisions": [{"decision": "approved"}] * 28 + [{"decision": "needs_edit"}] * 12 + [{"decision": "rejected"}] + [{"decision": "defer"}] * 46}
    review_queue = {"items": [{} for _ in range(87)]}
    gate = build_apply_route_consistency(
        blocks_payload=blocks_payload,
        apply_result_payload=apply_result,
        decisions_overlay_payload=decisions_overlay,
        review_queue_payload=review_queue,
    )
    assert gate["apply_route_consistency_passed"] is False
    assert "b1" in gate["forbidden_route_markers"]
