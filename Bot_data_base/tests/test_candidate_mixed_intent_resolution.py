from __future__ import annotations

from tools.clean_source_reprocess import build_mixed_intent_audit_report


def _mk_block(block_id: str, text: str, chunk_type: str = "theory", allowed_use: list[str] | None = None) -> dict:
    return {
        "id": block_id,
        "text": text,
        "source": "book:123__кузница_духа",
        "metadata": {
            "source_id": "123__кузница_духа",
            "governance": {
                "chunk_type": chunk_type,
                "allowed_use": allowed_use or ["writer_context", "practice_suggestion"],
                "safety_flags": ["not_for_direct_quote"],
            },
            "chunking_quality": {
                "mixed_intent_risk": True,
                "mixed_intent_severity": "medium",
                "mixed_intent_reason": "ambiguous_primary_with_secondary_markers",
                "primary_role": "theory",
                "secondary_role_markers": ["practice"],
            },
        },
    }


def test_mixed_intent_resolution_dialogue_becomes_false_positive() -> None:
    block = _mk_block(
        "r1",
        "> Из сессии: клиент пробовал практику, а терапевт объясняет, почему реакция нормальна.",
    )
    report = build_mixed_intent_audit_report(source_prd="PRD-046.0.8-HF2", candidate_blocks=[block])

    assert report["mixed_intent_false_positive_count"] == 1
    assert report["mixed_intent_unresolved_count"] == 0
    q = block["metadata"]["chunking_quality"]
    assert q["mixed_intent_resolution"] == "false_positive"
    assert q["mixed_intent_risk"] is False
    assert q["mixed_intent_severity"] == "low"


def test_mixed_intent_resolution_strips_practice_suggestion_for_non_practice_primary() -> None:
    block = _mk_block(
        "r2",
        "Теоретический фрагмент о практике без пошагового протокола.",
        chunk_type="theory",
        allowed_use=["writer_context", "practice_suggestion"],
    )
    report = build_mixed_intent_audit_report(source_prd="PRD-046.0.8-HF2", candidate_blocks=[block])

    assert report["mixed_intent_primary_role_resolved_count"] == 1
    gov = block["metadata"]["governance"]
    assert gov["chunk_type"] == "theory"
    assert "practice_suggestion" not in gov["allowed_use"]
