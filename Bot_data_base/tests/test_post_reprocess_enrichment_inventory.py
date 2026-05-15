from __future__ import annotations

from tools.llm_enrichment_post_reprocess import build_inventory


def test_inventory_contains_safe_preview_and_hash_only() -> None:
    blocks = [
        {
            "id": "b1",
            "text": "Очень длинный текст " * 50,
            "source": "book:123__кузница_духа",
            "metadata": {
                "source_title": "Кузница Духа",
                "heading_path": ["Глава 1", "Раздел 1"],
                "governance": {
                    "chunk_type": "practice",
                    "allowed_use": ["writer_context", "practice_suggestion"],
                    "safety_flags": ["not_for_direct_quote", "practice_requires_low_resource_check"],
                    "lens_family": ["self_criticism"],
                },
                "chunking_quality": {"mixed_intent_severity": "low", "boundary_confidence": 0.8},
            },
        }
    ]
    payload = build_inventory(blocks)
    assert payload["blocks_total"] == 1
    item = payload["items"][0]
    assert item["block_id"] == "b1"
    assert item["source_id"] == "123__кузница_духа"
    assert len(item["safe_preview"]) <= 400
    assert len(item["raw_text_hash"]) == 64
    assert "text" not in item
    assert "raw_full_text" not in item
