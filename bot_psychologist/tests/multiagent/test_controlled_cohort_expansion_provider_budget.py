from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_controlled_cohort_expansion as gate


def test_controlled_cohort_expansion_provider_budget_gate() -> None:
    payload = gate.build_provider_budget_gate(
        provider_calls_total=12,
        target_provider_calls_total=12,
        normal_user_provider_calls_total=0,
    )
    assert payload["provider_budget_gate_passed"] is True
    assert payload["provider_budget_exceeded"] is False

