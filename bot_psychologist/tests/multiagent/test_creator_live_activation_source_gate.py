from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_creator_live_activation as gate  # noqa: E402


def test_creator_live_activation_source_gate() -> None:
    preflight = gate.preflight_source(Path("TO_DO_LIST/logs/PRD-046.1.33"), Path("TO_DO_LIST/reports"))
    payload = gate.build_source_gate(preflight)
    assert preflight["ok"] is True
    assert payload["source_gate_passed"] is True
