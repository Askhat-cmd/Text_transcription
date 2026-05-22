from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_creator_live_activation as gate  # noqa: E402


def test_safety_kb_boundary_gate() -> None:
    payload = gate.build_safety_kb_boundary_gate()
    assert payload["safety_kb_boundary_gate_passed"] is True
