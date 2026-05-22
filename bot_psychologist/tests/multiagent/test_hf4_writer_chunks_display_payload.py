from __future__ import annotations

from pathlib import Path
import sys

CURRENT_FILE = Path(__file__).resolve()
BOT_PSYCHOLOGIST_ROOT = CURRENT_FILE.parents[2]
if str(BOT_PSYCHOLOGIST_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_PSYCHOLOGIST_ROOT))

from api.debug_routes import _build_semantic_hit_trace_list  # noqa: E402


def test_hf4_writer_chunks_payload_uses_safe_preview_fallback() -> None:
    traces = _build_semantic_hit_trace_list(
        [
            {
                "chunk_id": "c1",
                "source": "book",
                "score": 0.052,
                "content_preview": "safe preview",
            }
        ]
    )
    assert len(traces) == 1
    assert traces[0].content_preview == "safe preview"
    assert traces[0].content_full == "safe preview"

