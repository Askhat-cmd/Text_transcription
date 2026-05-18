from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.contracts.diagnostic_center_runtime_pilot_readiness_v1 import (
    DiagnosticCenterRuntimePilotReadinessDecision,
    DiagnosticCenterRuntimePilotReadinessStatus,
)


def test_runtime_pilot_readiness_contract_defaults() -> None:
    status = DiagnosticCenterRuntimePilotReadinessStatus().to_dict()
    decision = DiagnosticCenterRuntimePilotReadinessDecision().to_dict()
    assert status["decision"] == "blocked_runtime_pilot_readiness"
    assert decision["prd_id"] == "PRD-046.1.19"
