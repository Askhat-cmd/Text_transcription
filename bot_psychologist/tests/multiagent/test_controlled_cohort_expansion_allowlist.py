from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_controlled_cohort_expansion as gate


def test_controlled_cohort_expansion_allowlist_violation_detected() -> None:
    scenarios = [
        {"scenario_id": "ok", "target_user_id": "pilot_runtime_operator_003", "expected_response_goal": "x", "expected_micro_shift": "y"},
        {"scenario_id": "bad", "target_user_id": "unknown_user", "expected_response_goal": "x", "expected_micro_shift": "y"},
    ]
    policy = gate.build_cohort_policy(scenarios)
    assert policy["allowlist_violation_count"] == 1
    assert policy["cohort_policy_passed"] is False

