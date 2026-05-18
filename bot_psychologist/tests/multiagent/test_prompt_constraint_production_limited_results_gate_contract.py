from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.contracts.prompt_constraint_production_limited_results_gate_v1 import (
    PromptConstraintProductionLimitedResultsGateV1,
)


def test_production_limited_results_gate_contract_schema_version() -> None:
    payload = PromptConstraintProductionLimitedResultsGateV1().to_dict()
    assert payload["schema_version"] == "prompt_constraint_production_limited_results_gate_v1"
    assert payload["prd"] == "PRD-046.1.14"
