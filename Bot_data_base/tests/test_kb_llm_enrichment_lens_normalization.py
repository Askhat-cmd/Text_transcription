from __future__ import annotations

from tools.kb_llm_enrichment import _normalize_lens_candidates


def test_allowlist_lens_values_preserved() -> None:
    normalized = _normalize_lens_candidates(["self_criticism", "low_resource", "self_criticism"])
    assert normalized["allowed"] == ["self_criticism", "low_resource"]
    assert normalized["unmapped"] == []


def test_russian_synonyms_normalized_to_canonical() -> None:
    normalized = _normalize_lens_candidates(["самокритика", "стыд", "тревога"])
    assert normalized["allowed"] == ["self_criticism", "shame", "anxiety"]
    assert normalized["unmapped"] == []


def test_unknown_lens_filtered_out_and_tracked() -> None:
    normalized = _normalize_lens_candidates(["unknown_new_lens", "самокритика"])
    assert normalized["allowed"] == ["self_criticism"]
    assert normalized["unmapped"] == ["unknown_new_lens"]
