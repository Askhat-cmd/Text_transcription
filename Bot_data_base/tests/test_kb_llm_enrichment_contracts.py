from __future__ import annotations

from knowledge_governance.enrichment_contracts import (
    ENRICHMENT_SCHEMA_VERSION,
    EnrichmentCandidate,
    LLMMetadata,
)


def test_enrichment_candidate_from_payload_serializes_lists() -> None:
    payload = {
        "summary_candidate": "Короткая безопасная переформулировка смыслового фрагмента без дословного цитирования источника.",
        "lens_family_candidates": ["self_criticism", "meaning", ""],
        "tags": ["practice", "self_criticism", "practice"],
        "use_when": ["когда нужна мягкая фокусировка внимания"],
        "avoid_when": ["когда состояние остро нестабильно"],
        "self_contained_score": 0.71,
        "self_contained_reason": "Сохраняет ядро смысла и условие применения.",
        "split_merge_suggestion": {"action": "keep", "reason": "Семантическая целостность сохранена."},
        "confidence": 0.66,
        "needs_human_review": False,
        "review_reasons": [],
    }
    metadata = LLMMetadata(provider="mock", model="mock-kb-enrichment-v1", mock=True)
    candidate = EnrichmentCandidate.from_llm_payload(
        llm_payload=payload,
        block_id="b-1",
        source_title="Кузница Духа",
        chunk_type_original="practice",
        allowed_use_original=["writer_context", "practice_suggestion"],
        safety_flags_original=["not_for_direct_quote", "practice_requires_low_resource_check"],
        llm_metadata=metadata,
    )

    serialized = candidate.to_dict()
    assert serialized["schema_version"] == ENRICHMENT_SCHEMA_VERSION
    assert serialized["block_id"] == "b-1"
    assert serialized["chunk_type_original"] == "practice"
    assert serialized["allowed_use_original"] == ["writer_context", "practice_suggestion"]
    assert serialized["safety_flags_original"] == ["not_for_direct_quote", "practice_requires_low_resource_check"]
    assert serialized["lens_family_candidates"] == ["self_criticism", "meaning"]
    assert serialized["split_merge_suggestion"]["action"] == "keep"

