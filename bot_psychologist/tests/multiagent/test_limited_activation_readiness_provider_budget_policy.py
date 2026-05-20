from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_limited_activation_readiness as gate  # noqa: E402


def test_limited_activation_readiness_provider_budget_policy_gate() -> None:
    payload = gate.build_provider_budget_policy_gate()
    assert payload["provider_budget_policy_gate_passed"] is True
    assert payload["provider_called_by_prd_046_1_33"] is False
    assert payload["max_provider_calls_recommended"] <= 10

