from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_limited_smoke_consolidation as gate


def test_limited_smoke_consolidation_source_gate() -> None:
    preflight = gate.preflight_source_chain(
        [
            Path("TO_DO_LIST/logs/PRD-046.1.23"),
            Path("TO_DO_LIST/logs/PRD-046.1.24"),
            Path("TO_DO_LIST/logs/PRD-046.1.25"),
        ],
        Path("TO_DO_LIST/reports"),
    )
    payload = gate.build_source_gate(preflight)
    assert payload["source_chain_complete"] is True
    assert payload["source_gate_passed"] is True

