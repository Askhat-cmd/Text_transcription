from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_second_provider_backed_smoke as gate


def test_second_provider_backed_smoke_source_gate() -> None:
    preflight = gate.preflight_source(Path("TO_DO_LIST/logs/PRD-046.1.24"), Path("TO_DO_LIST/reports"))
    payload = gate.build_source_gate(preflight["parsed"], preflight["ok"])
    assert payload["source_gate_passed"] is True
    assert payload["source_024_decision"] == "continue_limited_candidate"
