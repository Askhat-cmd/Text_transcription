from __future__ import annotations

from pathlib import Path

from knowledge_governance.mechanism_metadata import adapt_block_to_mechanism_metadata
from knowledge_governance.offline_enrichment import (
    ENRICHMENT_CANDIDATE_SCHEMA_VERSION,
    build_deterministic_candidate,
    build_enrichment_schema_snapshot,
    validate_enrichment_candidate,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


def _block(
    *,
    block_id: str = "b1",
    title: str = "Контроль как защита",
    summary: str = "Контроль помогает удерживать безопасность, но сужает свободу.",
    text: str = "Когда тревога растет, человек усиливает контроль и старается не чувствовать уязвимость.",
    chunk_type: str = "lens",
    allowed_use: list[str] | None = None,
    safety_flags: list[str] | None = None,
    practice_metadata: dict | None = None,
) -> dict:
    governance = {
        "schema_version": "governance_v1",
        "chunk_type": chunk_type,
        "allowed_use": allowed_use or ["writer_context", "diagnostic_lens"],
        "safety_flags": safety_flags or ["not_for_direct_quote"],
        "source_trace": {"source_id": "src1", "source_title": "Source One", "source_type": "book"},
    }
    if practice_metadata is not None:
        governance["practice_metadata"] = practice_metadata
    return {
        "id": block_id,
        "title": title,
        "summary": summary,
        "text": text,
        "source": "book:src1",
        "metadata": {
            "source_title": "Source One",
            "source_type": "book",
            "heading_path": ["ГЛАВА 1. Тест", "Раздел"],
            "governance": governance,
            "chunking_quality": {"schema_version": "chunking_quality_v1"},
        },
    }


def test_schema_snapshot_exposes_candidate_contract() -> None:
    snapshot = build_enrichment_schema_snapshot()
    assert snapshot["schema_version"] == ENRICHMENT_CANDIDATE_SCHEMA_VERSION
    assert "source_ref" in snapshot["required_fields"]
    assert snapshot["invariants"]["safe_to_apply_automatically"] is False


def test_deterministic_candidate_is_manual_review_only() -> None:
    raw = _block()
    metadata, _ = adapt_block_to_mechanism_metadata(raw)
    result = build_deterministic_candidate(
        repo_root=REPO_ROOT,
        source_id="src1",
        source_doc="Source One",
        raw_block=raw,
        metadata=metadata,
        selection_reasons=["missing_mechanism_hints"],
    )
    candidate = result.candidate
    assert candidate["status"] == "candidate_only"
    assert candidate["governance_review"]["safe_to_apply_automatically"] is False
    assert candidate["governance_review"]["manual_review_required"] is True
    assert candidate["generation"]["mode"] == "deterministic"
    assert len(candidate["source_ref"]["content_preview"]) <= 300
    assert result.validation["errors"] == []


def test_invalid_depth_level_suggestion_is_rejected() -> None:
    candidate = {
        "schema_version": ENRICHMENT_CANDIDATE_SCHEMA_VERSION,
        "source_ref": {"source_id": "src", "source_doc": "Doc", "block_id": "b", "heading_path": ["H"], "content_preview": "preview"},
        "current_metadata_summary": {"chunk_type": "concept"},
        "candidate_fields": {"depth_level_suggestion": 7, "quote_policy_suggestion": "paraphrase_only"},
        "grounding": {"grounded_in_source_preview": True, "source_terms_used": [], "unsupported_claims": [], "needs_source_context": False},
        "governance_review": {"safe_to_apply_automatically": False, "manual_review_required": True, "manual_review_reasons": [], "blocked_reasons": [], "risk_level": "low"},
        "generation": {"mode": "deterministic", "model": "", "prompt_version": "", "provider_payload_committed": False, "created_at": "now"},
        "confidence": 0.4,
        "status": "candidate_only",
    }
    validation = validate_enrichment_candidate(candidate)
    assert "invalid_depth_level_suggestion" in validation["errors"]


def test_practice_without_contraindications_gets_warning() -> None:
    raw = _block(
        chunk_type="practice",
        title="Три выдоха",
        summary="Короткая практика.",
        text="Шаг 1. Заметь напряжение.\nШаг 2. Сделай медленный выдох.",
        allowed_use=["writer_context", "practice_suggestion"],
        practice_metadata={"duration": "3 min", "preconditions": ["user_has_some_capacity"]},
    )
    metadata, _ = adapt_block_to_mechanism_metadata(raw)
    result = build_deterministic_candidate(
        repo_root=REPO_ROOT,
        source_id="src1",
        source_doc="Source One",
        raw_block=raw,
        metadata=metadata,
        selection_reasons=["practice_missing_contraindications"],
    )
    assert "practice_current_metadata_missing_contraindications" in result.validation["warnings"]


def test_diagnostic_lens_without_translation_gets_warning() -> None:
    candidate = {
        "schema_version": ENRICHMENT_CANDIDATE_SCHEMA_VERSION,
        "source_ref": {"source_id": "src", "source_doc": "Doc", "block_id": "b", "heading_path": ["H"], "content_preview": "preview"},
        "current_metadata_summary": {"chunk_type": "diagnostic_lens"},
        "candidate_fields": {
            "depth_level_suggestion": 2,
            "quote_policy_suggestion": "internal_only",
            "safe_user_translation_candidate": "",
            "contraindications_candidates": [],
        },
        "grounding": {"grounded_in_source_preview": True, "source_terms_used": [], "unsupported_claims": [], "needs_source_context": False},
        "governance_review": {"safe_to_apply_automatically": False, "manual_review_required": True, "manual_review_reasons": [], "blocked_reasons": [], "risk_level": "medium"},
        "generation": {"mode": "deterministic", "model": "", "prompt_version": "", "provider_payload_committed": False, "created_at": "now"},
        "confidence": 0.4,
        "status": "candidate_only",
    }
    validation = validate_enrichment_candidate(candidate)
    assert "diagnostic_lens_missing_safe_user_translation" in validation["warnings"]


def test_forbidden_content_full_key_is_blocked() -> None:
    candidate = {
        "schema_version": ENRICHMENT_CANDIDATE_SCHEMA_VERSION,
        "source_ref": {
            "source_id": "src",
            "source_doc": "Doc",
            "block_id": "b",
            "heading_path": ["H"],
            "content_preview": "preview",
            "content_full": "must not exist",
        },
        "current_metadata_summary": {"chunk_type": "concept"},
        "candidate_fields": {"depth_level_suggestion": 1, "quote_policy_suggestion": "paraphrase_only"},
        "grounding": {"grounded_in_source_preview": True, "source_terms_used": [], "unsupported_claims": [], "needs_source_context": False},
        "governance_review": {"safe_to_apply_automatically": False, "manual_review_required": True, "manual_review_reasons": [], "blocked_reasons": [], "risk_level": "low"},
        "generation": {"mode": "deterministic", "model": "", "prompt_version": "", "provider_payload_committed": False, "created_at": "now"},
        "confidence": 0.4,
        "status": "candidate_only",
    }
    validation = validate_enrichment_candidate(candidate)
    assert "forbidden_keys_present" in validation["errors"]
