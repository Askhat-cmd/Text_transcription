from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_provider_backed_limited_smoke_execution as execution


def test_provider_backed_limited_smoke_source_gate() -> None:
    preflight = execution.preflight_source(
        Path("TO_DO_LIST/logs/PRD-046.1.22"),
        Path("TO_DO_LIST/reports"),
    )
    gate = execution.build_source_gate(preflight["parsed"], preflight["ok"])
    assert gate["source_gate_passed"] is True
