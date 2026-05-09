from __future__ import annotations

from tools.kb_llm_enrichment import _normalize_review_reasons


def test_controlled_review_reasons_preserved() -> None:
    reasons, notes = _normalize_review_reasons(["low_confidence", "lens_mapping_uncertain"])
    assert reasons == ["low_confidence", "lens_mapping_uncertain"]
    assert notes == []


def test_free_form_review_reason_moves_to_notes() -> None:
    reasons, notes = _normalize_review_reasons([
        "Нужна дополнительная проверка соответствия контексту",
        "insufficient_context",
    ])
    assert reasons == ["insufficient_context"]
    assert len(notes) == 1


def test_russian_review_reason_synonym_normalized() -> None:
    reasons, notes = _normalize_review_reasons(["низкая уверенность"])
    assert reasons == ["low_confidence"]
    assert notes == []
