from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.contracts.diagnostic_center_stabilization_v1 import (
    DiagnosticCenterStabilizationRunV1,
)


def test_diagnostic_center_stabilization_contract_schema_version() -> None:
    payload = DiagnosticCenterStabilizationRunV1().to_dict()
    assert payload["schema_version"] == "diagnostic_center_stabilization_v1"
    assert payload["prd"] == "PRD-046.1.15"
