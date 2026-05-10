from __future__ import annotations

import json
from pathlib import Path

from review.review_queue_builder import build_review_queue
from review.review_sanitizer import find_forbidden_review_keys


def _block(
    *,
    block_id: str,
    text: str = "safe text",
    confidence: float = 0.5,
    needs_human_review: bool = True,
    split_action: str = "keep",
    mixed_intent_severity: str = "low",
    allowed_use: list[str] | None = None,
) -> dict:
    return {
        "id": block_id,
        "source": "book:source_1",
        "title": "title",
        "summary": "summary",
        "text": text,
        "metadata": {
            "source_title": "Source title",
            "governance": {
                "chunk_type": "lens",
                "allowed_use": allowed_use or ["writer_context", "diagnostic_lens"],
                "safety_flags": ["not_for_direct_quote"],
                "lens_family": ["shame"],
            },
            "chunking_quality": {
                "mixed_intent_severity": mixed_intent_severity,
            },
            "llm_enrichment": {
                "schema_version": "kb_llm_enrichment_v1",
                "summary": "candidate summary",
                "lens_family_candidates": ["shame"],
                "tags": ["tag1"],
                "use_when": ["use"],
                "avoid_when": ["avoid"],
                "self_contained_score": 0.7,
                "self_contained_reason": "reason",
                "split_merge_suggestion": {"action": split_action, "reason": "why"},
                "confidence": confidence,
                "needs_human_review": needs_human_review,
                "review_status": "machine_candidate_needs_human_review",
                "review_reasons": ["summary_quality_uncertain"],
                "llm_metadata": {"provider": "openai", "model": "gpt-4o-mini", "prompt_version": "v1", "mock": False},
            },
        },
    }


def test_queue_includes_needs_human_review(tmp_path: Path) -> None:
    payload = {"blocks": [_block(block_id="b1")]}
    input_path = tmp_path / "all_blocks_merged.json"
    input_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    queue = build_review_queue(input_path=input_path, max_items=200, source_prd="PRD-046.0.7")
    assert queue["review_items_count"] == 1
    assert queue["items"][0]["block_id"] == "b1"


def test_low_confidence_priority_and_split_merge_action(tmp_path: Path) -> None:
    payload = {"blocks": [_block(block_id="b1", confidence=0.5, split_action="split")]}
    input_path = tmp_path / "all_blocks_merged.json"
    input_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    queue = build_review_queue(input_path=input_path, max_items=200, source_prd="PRD-046.0.7")
    item = queue["items"][0]
    assert item["review_priority"] in {"P0", "P1"}
    assert item["recommended_action"] == "split_merge_review"


def test_queue_has_no_forbidden_keys_and_no_mutation(tmp_path: Path) -> None:
    payload = {"blocks": [_block(block_id="b1", text="x" * 500)]}
    input_path = tmp_path / "all_blocks_merged.json"
    before = json.dumps(payload, ensure_ascii=False, indent=2)
    input_path.write_text(before, encoding="utf-8")
    queue = build_review_queue(input_path=input_path, max_items=200, source_prd="PRD-046.0.7")
    assert queue["source_mutated"] is False
    assert queue["input_file_sha256_before"] == queue["input_file_sha256_after"]
    assert find_forbidden_review_keys(queue) == []
    assert all(len(item["content_preview"]) <= 240 for item in queue["items"])

