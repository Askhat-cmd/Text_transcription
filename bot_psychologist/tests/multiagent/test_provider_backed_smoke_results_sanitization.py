from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_provider_backed_smoke_results_gate as gate


def test_provider_backed_smoke_results_sanitization_passed() -> None:
    preflight = gate.preflight_source(Path("TO_DO_LIST/logs/PRD-046.1.23"), Path("TO_DO_LIST/reports"))
    provider_review = gate.build_provider_output_sanitization_consolidation(preflight["parsed"])
    trace_review = gate.build_trace_sanitization_consolidation(preflight["parsed"])
    assert provider_review["provider_output_sanitization_consolidation_status"] == "passed"
    assert trace_review["trace_sanitization_consolidation_status"] == "passed"

