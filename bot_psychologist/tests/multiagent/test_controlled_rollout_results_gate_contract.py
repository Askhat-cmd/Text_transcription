from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.contracts.diagnostic_center_controlled_rollout_results_gate_v1 import (  # noqa: E402
    ControlledRolloutResultsGateDecisionV1,
)


def test_controlled_rollout_results_gate_contract_defaults() -> None:
    payload = ControlledRolloutResultsGateDecisionV1().to_dict()
    assert payload["schema_version"] == "diagnostic_center_controlled_rollout_results_gate_decision_v1"
    assert payload["prd_id"] == "PRD-046.1.32"
