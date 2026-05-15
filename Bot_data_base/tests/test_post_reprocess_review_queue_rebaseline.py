from __future__ import annotations

from tools.llm_enrichment_post_reprocess import build_review_queue_rebaseline


def test_review_queue_rebaseline_collects_flags_and_priorities() -> None:
    inventory = {
        "items": [
            {
                "block_id": "b1",
                "source_id": "123__кузница_духа",
                "source_title": "Кузница Духа",
                "chunk_type": "practice",
                "safety_flags": ["not_for_direct_quote", "source_style_not_user_facing"],
                "safe_preview": "preview",
            }
        ]
    }
    overlay = {
        "items": [
            {
                "block_id": "b1",
                "advisory": {
                    "summary": "",
                    "use_when": [],
                    "avoid_when": [],
                    "lens_family_candidates": [],
                },
                "quality": {
                    "confidence": 0.3,
                    "self_contained_score": 0.4,
                    "needs_human_review": True,
                    "review_reasons": ["provider_unavailable"],
                },
            }
        ]
    }
    validation = {"warnings": [{"block_id": "b1", "code": "low_resource_avoid_when_missing"}]}
    queue = build_review_queue_rebaseline(overlay=overlay, inventory=inventory, validation=validation)
    assert queue["review_items_count"] == 1
    assert queue["priority_counts"]["P0"] == 1
    reasons = set(queue["items"][0]["review_reasons"])
    assert "provider_unavailable" in reasons
    assert "low_resource_avoid_when_missing" in reasons
