from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.contracts.prompt_constraint_supervised_rollout_v1 import (
    PromptConstraintSupervisedRolloutPlanV1,
)


def test_supervised_rollout_contract_schema_defaults() -> None:
    payload = PromptConstraintSupervisedRolloutPlanV1().to_dict()
    assert payload["schema_version"] == "prompt_constraint_supervised_rollout_plan_v1"
    assert payload["prd"] == "PRD-046.1.8"
    assert payload["rollout_stage"] == "plan_only"
    assert payload["next_decision_options"] == [
        "execution_blocked",
        "ready_for_supervised_execution_prd",
        "hotfix_required",
    ]
