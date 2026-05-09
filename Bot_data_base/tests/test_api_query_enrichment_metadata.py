import sys
import types
from importlib.machinery import ModuleSpec

if "yt_dlp" not in sys.modules:
    yt_dlp_stub = types.ModuleType("yt_dlp")
    yt_dlp_stub.__spec__ = ModuleSpec(name="yt_dlp", loader=None)

    class _DummyYoutubeDL:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def extract_info(self, *args, **kwargs):
            return {}

    yt_dlp_stub.YoutubeDL = _DummyYoutubeDL
    sys.modules["yt_dlp"] = yt_dlp_stub

from api.routes.query import _build_chunk_result


def test_build_chunk_result_includes_llm_enrichment_metadata() -> None:
    candidate = {
        "chunk_id": "chunk_1",
        "content": "Текст",
        "score": 0.8,
        "metadata": {
            "sd_level": "GREEN",
            "author_id": "author_1",
            "author": "Author",
            "source_type": "book",
            "title": "Блок",
            "keywords": ["k1"],
            "governance_schema_version": "governance_v1",
            "governance_chunk_type": "practice",
            "governance_allowed_use": "writer_context,practice_suggestion",
            "governance_safety_flags": "requires_grounding,not_for_direct_quote",
            "governance_lens_family": "somatic,avoidance",
            "llm_enrichment_schema_version": "kb_llm_enrichment_v1",
            "llm_enrichment_applied_from_prd": "PRD-046.0.5-APPLY1",
            "llm_enrichment_source_overlay": "PRD-046.0.5-RUN1-HF3",
            "llm_enrichment_status": "applied_candidate",
            "llm_enrichment_review_status": "machine_candidate_needs_human_review",
            "llm_enrichment_summary": "safe summary",
            "llm_enrichment_lens_family_candidates": "self_criticism,avoidance",
            "llm_enrichment_tags": "practice,self_criticism",
            "llm_enrichment_use_when": "when needed",
            "llm_enrichment_avoid_when": "when low resource",
            "llm_enrichment_confidence": 0.67,
            "llm_enrichment_needs_human_review": "true",
            "llm_enrichment_review_reasons": "summary_quality_uncertain",
            "llm_enrichment_provider": "openai",
            "llm_enrichment_model": "gpt-4o-mini",
            "llm_enrichment_prompt_version": "kb_enrichment_v1_3",
            "llm_enrichment_mock": "false",
        },
    }

    result = _build_chunk_result(candidate)
    llm = result.governance["llm_enrichment"]
    assert llm["schema_version"] == "kb_llm_enrichment_v1"
    assert llm["summary"] == "safe summary"
    assert llm["tags"] == ["practice", "self_criticism"]
    assert llm["needs_human_review"] is True
    assert llm["llm_metadata"]["model"] == "gpt-4o-mini"
    assert result.governance["llm_enrichment_summary"] == "safe summary"
    assert result.governance["llm_enrichment_review_status"] == "machine_candidate_needs_human_review"
