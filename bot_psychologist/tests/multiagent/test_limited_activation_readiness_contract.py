from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.contracts.diagnostic_center_limited_activation_readiness_v1 import (  # noqa: E402
    ReadinessScorecard,
)


def test_limited_activation_readiness_contract_defaults() -> None:
    payload = ReadinessScorecard().to_dict()
    assert payload["schema_version"] == "diagnostic_center_limited_activation_readiness_scorecard_v1"
    assert payload["prd_id"] == "PRD-046.1.33"

