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


def test_build_chunk_result_returns_governance_summary() -> None:
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
            "governance_low_resource_safe": "true",
            "governance_not_for_direct_quote": "true",
            "governance_source_style_not_user_facing": "false",
            "section_role_hint": "practice",
            "heading_path_text": "Manual > Practice",
            "mixed_intent_risk": "false",
            "chunking_quality_notes": "missing_summary",
            "split_reason": "practice_preserved",
        },
    }

    result = _build_chunk_result(candidate)
    assert result.governance["schema_version"] == "governance_v1"
    assert result.governance["chunk_type"] == "practice"
    assert result.governance["allowed_use"] == ["writer_context", "practice_suggestion"]
    assert result.governance["not_for_direct_quote"] is True
    assert result.governance["chunking_quality"]["section_role_hint"] == "practice"
    assert result.governance["chunking_quality"]["heading_path_present"] is True


def test_build_chunk_result_without_governance_returns_empty_dict() -> None:
    candidate = {
        "chunk_id": "chunk_2",
        "content": "Текст",
        "score": 0.4,
        "metadata": {
            "sd_level": "BLUE",
            "author_id": "author_2",
            "author": "Author",
            "source_type": "book",
            "title": "Блок",
            "keywords": [],
        },
    }

    result = _build_chunk_result(candidate)
    assert result.governance == {}
