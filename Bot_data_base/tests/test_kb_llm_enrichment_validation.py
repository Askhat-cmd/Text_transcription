from __future__ import annotations

from knowledge_governance.enrichment_contracts import EnrichmentCandidate, LLMMetadata
from knowledge_governance.enrichment_validators import (
    check_forbidden_keys,
    validate_candidate,
    validate_governance_invariants,
)


def _candidate(**overrides: object) -> EnrichmentCandidate:
    candidate = EnrichmentCandidate(
        block_id="block-1",
        source_title="Кузница Духа",
        chunk_type_original="practice",
        allowed_use_original=["writer_context", "practice_suggestion"],
        safety_flags_original=["not_for_direct_quote", "practice_requires_low_resource_check"],
        summary_candidate="Смысловой фрагмент описывает паттерн переживания и контекст, где полезно мягко стабилизироваться, "
        "сфокусироваться на телесных маркерах и выбрать бережный следующий шаг без директивности и давления.",
        lens_family_candidates=["self_criticism", "low_resource"],
        tags=["practice", "self_criticism"],
        use_when=["когда важно стабилизировать внимание без перегруза"],
        avoid_when=["когда мало сил или выраженная перегрузка"],
        self_contained_score=0.72,
        self_contained_reason="Достаточно контекста без прямого цитирования.",
        confidence=0.7,
        llm_metadata=LLMMetadata(),
    )
    for key, value in overrides.items():
        setattr(candidate, key, value)
    return candidate


def test_validate_candidate_flags_unknown_lens_and_low_resource_guard() -> None:
    candidate = _candidate(
        lens_family_candidates=["self_criticism", "unknown_new_lens"],
        avoid_when=["когда есть сомнения"],
    )
    result = validate_candidate(candidate=candidate, source_text="Оригинальный текст фрагмента для проверки.")
    assert result.passed is False
    assert "unknown_lens_candidate" in result.reasons
    assert "low_resource_avoid_when_missing" in result.reasons


def test_validate_candidate_detects_long_quote_risk() -> None:
    source_text = (
        "Это длинный исходный фрагмент, который не должен попадать в summary дословно. "
        "Он содержит специфические формулировки и последовательности."
    )
    candidate = _candidate(summary_candidate=source_text + " Дополнительный хвост.")
    result = validate_candidate(candidate=candidate, source_text=source_text)
    assert "summary_direct_quote_risk" in result.reasons
    assert result.reason_details.get("summary_direct_quote_risk") == "prefix_overlap"


def test_validate_governance_invariants() -> None:
    source_block = {
        "metadata": {
            "governance": {
                "chunk_type": "practice",
                "allowed_use": ["writer_context", "practice_suggestion"],
                "safety_flags": ["not_for_direct_quote", "practice_requires_low_resource_check"],
            }
        }
    }
    candidate = _candidate()
    violations = validate_governance_invariants(candidate=candidate, source_block=source_block)
    assert violations == []


def test_check_forbidden_keys_recursive() -> None:
    payload = {
        "a": [{"ok": 1}, {"meta": {"raw_llm_prompt_with_text": "hidden"}}],
        "nested": {"api_key": "secret"},
    }
    hits = check_forbidden_keys(payload)
    assert "raw_llm_prompt_with_text" in hits
    assert "api_key" in hits
