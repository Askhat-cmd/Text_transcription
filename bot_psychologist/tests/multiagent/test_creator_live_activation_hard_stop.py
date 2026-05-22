from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_creator_live_activation as gate  # noqa: E402


def test_hard_stop_gate_passes_on_green_inputs() -> None:
    payload = gate.build_hard_stop_gate(
        normal_user_gate={"normal_user_no_effect_gate_passed": True},
        provider_budget_gate={"provider_budget_gate_passed": True},
        trace_gate={"trace_provider_sanitization_gate_passed": True},
        safety_gate={"safety_kb_boundary_gate_passed": True},
        rollback_gate={"rollback_kill_switch_gate_passed": True},
    )
    assert payload["hard_stop_gate_passed"] is True
    assert payload["hard_stop_triggered"] is False
