from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.contracts.diagnostic_center_runtime_pilot_execution_v1 import (
    DiagnosticCenterRuntimePilotExecutionStatus,
)


def test_runtime_pilot_execution_contract_defaults() -> None:
    payload = DiagnosticCenterRuntimePilotExecutionStatus().to_dict()
    assert payload["final_status"] == "failed"
    assert payload["decision"] == "blocked_runtime_pilot_execution"

