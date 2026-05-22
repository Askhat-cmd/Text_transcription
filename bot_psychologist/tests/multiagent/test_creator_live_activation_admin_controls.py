from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_creator_live_activation as gate  # noqa: E402


def test_admin_runtime_controls_gate() -> None:
    source = {"source_gate_passed": True}
    creator = {"creator_identity_gate_passed": True}
    payload = gate.build_admin_runtime_controls_gate(source_gate=source, creator_identity_gate=creator)
    assert payload["admin_runtime_controls_gate_passed"] is True
    assert payload["runtime_mode_effective"] == "creator_only"
