from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_second_provider_backed_smoke as gate


def test_second_provider_backed_smoke_provider_budget_gate() -> None:
    passed = gate.build_provider_budget_gate(provider_calls_performed=6, normal_user_provider_calls=0)
    failed = gate.build_provider_budget_gate(provider_calls_performed=7, normal_user_provider_calls=1)
    assert passed["provider_budget_gate_passed"] is True
    assert failed["provider_budget_gate_passed"] is False
