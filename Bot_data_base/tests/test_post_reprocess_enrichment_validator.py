from __future__ import annotations

from tools.llm_enrichment_post_reprocess import validate_overlay


def _inventory() -> dict:
    return {
        "items": [
            {
                "block_id": "b1",
                "raw_text_hash": "h1",
                "safe_preview": "Это preview текста.",
                "safety_flags": ["not_for_direct_quote", "practice_requires_low_resource_check"],
                "chunk_type": "practice",
                "source_id": "123__кузница_духа",
                "source_title": "Кузница Духа",
            }
        ]
    }


def test_validator_detects_governance_mutation_and_invalid_fields() -> None:
    overlay = {
        "items": [
            {
                "block_id": "b1",
                "input_text_hash": "bad",
                "advisory": {
                    "summary": "Ты должен немедленно сделать так.",
                    "allowed_use": ["hijack"],
                    "use_when": [],
                    "avoid_when": [],
                },
                "quality": {"confidence": 2.0, "self_contained_score": "x", "needs_human_review": "yes"},
            }
        ]
    }
    result = validate_overlay(overlay=overlay, inventory=_inventory())
    assert result["passed"] is False
    codes = {e["code"] for e in result["errors"]}
    assert "governance_authority_mutation_attempt" in codes
    assert "input_text_hash_mismatch" in codes
    assert "directive_life_advice" in codes
    assert "invalid_confidence" in codes
    assert "invalid_self_contained_score" in codes
    assert "missing_review_status" in codes
