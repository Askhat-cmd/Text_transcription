from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_controlled_rollout_planning as planning


def test_controlled_rollout_planning_cohort_policy() -> None:
    payload = planning.build_cohort_policy()
    assert payload["max_target_users"] == 3
    assert payload["target_user_type"] == "allowlisted_internal_or_synthetic_operators_only"
    assert payload["ready"] is True
