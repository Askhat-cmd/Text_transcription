from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_controlled_rollout_execution as execution  # noqa: E402


def test_controlled_rollout_execution_provider_budget() -> None:
    execution_results = {
        "provider_calls_total": 12,
    }
    payload = execution.build_provider_budget_gate(execution_results=execution_results, provider_budget_max=12)
    assert payload["provider_budget_gate_passed"] is True
    assert payload["provider_calls_total"] == 12

