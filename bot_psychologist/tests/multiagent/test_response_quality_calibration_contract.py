from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.contracts.diagnostic_center_response_quality_calibration_v1 import (
    ResponseQualityCalibrationDecision,
    ResponseQualityCalibrationStatus,
)


def test_response_quality_calibration_contract_defaults() -> None:
    status = ResponseQualityCalibrationStatus().to_dict()
    decision = ResponseQualityCalibrationDecision().to_dict()
    assert status["final_status"] == "blocked"
    assert decision["prd_id"] == "PRD-046.1.18"
