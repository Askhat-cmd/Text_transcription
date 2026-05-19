from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_final_runtime_governance_acceptance as gate


def test_final_runtime_governance_acceptance_boundary_decision() -> None:
    payload = gate.build_runtime_governance_boundary_decision()
    assert payload["diagnostic_center_runtime_status"] == "accepted_as_governed_limited_runtime_candidate"
    assert payload["broad_rollout_allowed"] is False
    assert payload["production_ready"] is False
    assert payload["normal_user_activation_allowed"] is False

