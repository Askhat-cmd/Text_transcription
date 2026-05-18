from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_final_acceptance as module


def test_runtime_governance_boundary_matrix_is_conservative() -> None:
    payload = module.build_runtime_governance_boundary_matrix()
    assert payload["diagnostic_center_v1"]["allowed_state"] == "trace_only_shadow"
    assert payload["diagnostic_center_v1"]["broad_runtime_authority"] is False
    assert payload["planner_bridge"]["can_apply_to_writer"] is False
    assert payload["prompt_constraint_pilot_runtime"]["normal_user_apply_allowed"] is False
    assert payload["prompt_constraint_pilot_runtime"]["broad_rollout_allowed"] is False
