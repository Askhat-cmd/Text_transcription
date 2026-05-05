import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from api.routes.common import _normalize_semantic_hits_detail_for_debug_trace_compat


def test_normalize_semantic_hits_detail_from_multiagent_shape() -> None:
    raw = [
        {
            "chunk_id": "abc",
            "score": 0.88,
            "content_preview": "preview",
            "content_full": "full text",
            "source": "memory",
        }
    ]
    expected = [
        {
            "block_id": "abc",
            "score": 0.88,
            "text_preview": "preview",
            "source": "memory",
        }
    ]
    assert _normalize_semantic_hits_detail_for_debug_trace_compat(raw) == expected


def test_normalize_semantic_hits_detail_handles_invalid_input() -> None:
    assert _normalize_semantic_hits_detail_for_debug_trace_compat(None) == []
    assert _normalize_semantic_hits_detail_for_debug_trace_compat(["x", 1, None]) == []
