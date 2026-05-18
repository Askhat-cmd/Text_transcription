from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.contracts.diagnostic_center_runtime_pilot_results_gate_v1 import (
    RuntimePilotResultsGateRunV1,
)


def test_runtime_pilot_results_gate_contract_defaults() -> None:
    payload = RuntimePilotResultsGateRunV1().to_dict()
    assert payload["schema_version"] == "diagnostic_center_runtime_pilot_results_gate_run_v1"
    assert payload["prd"] == "PRD-046.1.21"
