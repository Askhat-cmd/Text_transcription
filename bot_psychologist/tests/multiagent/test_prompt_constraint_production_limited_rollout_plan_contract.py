from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.contracts.prompt_constraint_production_limited_rollout_plan_v1 import (
    PromptConstraintProductionLimitedRolloutPlanV1,
)


def test_production_limited_rollout_plan_contract_schema_version() -> None:
    payload = PromptConstraintProductionLimitedRolloutPlanV1().to_dict()
    assert payload["schema_version"] == "prompt_constraint_production_limited_rollout_plan_v1"
    assert payload["prd"] == "PRD-046.1.12"
