from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_provider_backed_limited_smoke_execution as execution


def test_provider_backed_limited_smoke_trace_sanitization() -> None:
    trace = execution.build_trace_sanitization_review()
    assert trace["trace_sanitization_status"] == "passed"
    assert trace["contains_raw_provider_payload"] is False
