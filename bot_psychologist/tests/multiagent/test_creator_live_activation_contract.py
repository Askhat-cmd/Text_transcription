from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.contracts.diagnostic_center_creator_live_activation_v1 import LiveActivationScorecard  # noqa: E402


def test_creator_live_activation_contract_defaults() -> None:
    payload = LiveActivationScorecard().to_dict()
    assert payload["schema_version"] == "diagnostic_center_creator_live_activation_scorecard_v1"
    assert payload["prd_id"] == "PRD-046.1.34"
