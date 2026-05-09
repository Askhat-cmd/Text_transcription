import numpy as np

from models.universal_block import UniversalBlock
from storage.chroma_manager import ChromaManager


class DummyModel:
    def encode(self, texts, convert_to_numpy=True):
        return np.zeros((len(texts), 3), dtype=float)


def test_chroma_metadata_contains_llm_enrichment_fields(monkeypatch) -> None:
    monkeypatch.setattr(ChromaManager, "_init_embedding_model", lambda self: DummyModel())
    manager = ChromaManager(":memory:", "enrichment_test")
    block = UniversalBlock(
        text="Практика",
        title="Блок",
        source_type="book",
        source_id="src",
        sd_level="GREEN",
        governance={
            "schema_version": "governance_v1",
            "chunk_type": "practice",
            "allowed_use": ["writer_context"],
            "safety_flags": ["not_for_direct_quote"],
        },
        llm_enrichment={
            "schema_version": "kb_llm_enrichment_v1",
            "applied_from_prd": "PRD-046.0.5-APPLY1",
            "source_overlay": "PRD-046.0.5-RUN1-HF3",
            "status": "applied_candidate",
            "review_status": "machine_candidate_needs_human_review",
            "summary": "safe summary",
            "lens_family_candidates": ["self_criticism"],
            "tags": ["practice"],
            "use_when": ["when needed"],
            "avoid_when": ["when low resource"],
            "self_contained_score": 0.72,
            "self_contained_reason": "safe",
            "confidence": 0.65,
            "needs_human_review": True,
            "review_reasons": ["summary_quality_uncertain"],
            "llm_metadata": {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "prompt_version": "kb_enrichment_v1_3",
                "mock": False,
            },
        },
    )

    meta = manager._to_metadata(block)
    assert meta["llm_enrichment_schema_version"] == "kb_llm_enrichment_v1"
    assert meta["llm_enrichment_applied_from_prd"] == "PRD-046.0.5-APPLY1"
    assert meta["llm_enrichment_source_overlay"] == "PRD-046.0.5-RUN1-HF3"
    assert meta["llm_enrichment_review_status"] == "machine_candidate_needs_human_review"
    assert meta["llm_enrichment_summary"] == "safe summary"
    assert meta["llm_enrichment_tags"] == "practice"
    assert meta["llm_enrichment_needs_human_review"] == "true"
    assert meta["llm_enrichment_provider"] == "openai"
    assert meta["llm_enrichment_model"] == "gpt-4o-mini"
