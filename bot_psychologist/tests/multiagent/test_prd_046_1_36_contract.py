from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.contracts.diagnostic_center_creator_live_pilot_acceptance_v1 import (  # noqa: E402
    CreatorLivePilotAcceptanceScorecard,
)


def test_prd_046_1_36_scorecard_contract_defaults() -> None:
    payload = CreatorLivePilotAcceptanceScorecard().to_dict()
    assert payload["schema_version"] == "diagnostic_center_creator_live_pilot_acceptance_scorecard_v1"
    assert payload["final_status"] == "blocked"
    assert payload["decision"] == "blocked_creator_live_pilot"

