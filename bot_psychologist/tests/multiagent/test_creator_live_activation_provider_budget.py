from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_creator_live_activation as gate  # noqa: E402


def test_provider_budget_gate() -> None:
    payload = gate.build_provider_budget_gate(creator_calls=8, normal_calls=2)
    assert payload["provider_budget_gate_passed"] is True
    assert payload["total_provider_calls"] == 10
