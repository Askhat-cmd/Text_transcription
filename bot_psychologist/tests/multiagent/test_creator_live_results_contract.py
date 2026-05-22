from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.contracts.diagnostic_center_creator_live_results_gate_v1 import ResultsScorecard  # noqa: E402


def test_creator_live_results_contract_defaults() -> None:
    payload = ResultsScorecard().to_dict()
    assert payload["schema_version"] == "diagnostic_center_creator_live_results_scorecard_v1"
    assert payload["prd_id"] == "PRD-046.1.35"
    assert payload["decision"] == "blocked_fix_required"

