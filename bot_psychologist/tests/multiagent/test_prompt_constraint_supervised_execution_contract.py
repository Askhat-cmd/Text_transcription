from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.contracts.prompt_constraint_supervised_execution_v1 import (
    PromptConstraintSupervisedExecutionRunV1,
)


def test_supervised_execution_contract_schema_version() -> None:
    payload = PromptConstraintSupervisedExecutionRunV1().to_dict()
    assert payload["schema_version"] == "prompt_constraint_supervised_execution_v1"
    assert payload["prd"] == "PRD-046.1.9"
    assert payload["execution_mode"] == "controlled_harness"
