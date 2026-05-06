from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from api.models import DebugTrace


def test_debug_trace_model_keeps_quality_trace_fields() -> None:
    trace = DebugTrace(
        chunks_retrieved=[],
        llm_calls=[],
        context_written_to_memory="ctx",
        total_duration_ms=12,
        quality_trace_version="quality_trace_v1",
        quality_trace={
            "version": "quality_trace_v1",
            "summary_flags": ["generic_phrase_risk"],
        },
        quality_trace_error=None,
    )

    payload = trace.model_dump(exclude_none=True)
    assert payload["quality_trace_version"] == "quality_trace_v1"
    assert payload["quality_trace"]["summary_flags"] == ["generic_phrase_risk"]
    assert "quality_trace_error" not in payload

