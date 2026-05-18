from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.contracts.diagnostic_center_response_quality_eval_v1 import (
    ResponseQualityScorecard,
)


def test_response_quality_contract_defaults() -> None:
    payload = ResponseQualityScorecard().to_dict()
    assert payload["prd_id"] == "PRD-046.1.17"
    assert payload["decision"] == "blocked_source_gate_failed"
