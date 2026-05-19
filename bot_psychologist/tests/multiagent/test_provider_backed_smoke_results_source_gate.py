from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_provider_backed_smoke_results_gate as gate


def test_provider_backed_smoke_results_source_gate_passed() -> None:
    preflight = gate.preflight_source(Path("TO_DO_LIST/logs/PRD-046.1.23"), Path("TO_DO_LIST/reports"))
    assert preflight["ok"] is True
    source_gate = gate.build_source_gate(preflight["parsed"], preflight_ok=True)
    assert source_gate["source_gate_passed"] is True
    assert source_gate["source_decision"] == "provider_backed_limited_smoke_execution_passed"

