from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.contracts.diagnostic_center_controlled_cohort_expansion_v1 import (
    ControlledCohortExpansionDecisionV1,
    ControlledCohortExpansionStatusV1,
)


def test_controlled_cohort_expansion_contract_serialization() -> None:
    status = ControlledCohortExpansionStatusV1(
        final_status="passed",
        decision="ready_for_final_acceptance_and_stabilization_prd",
        target_user_count=3,
        scenario_count=12,
        provider_calls_total=12,
    ).to_dict()
    assert status["final_status"] == "passed"
    assert status["target_user_count"] == 3
    assert status["scenario_count"] == 12

    decision = ControlledCohortExpansionDecisionV1(
        final_status="passed",
        decision="ready_for_final_acceptance_and_stabilization_prd",
    ).to_dict()
    assert decision["schema_version"] == "diagnostic_center_controlled_cohort_expansion_decision_v1"
    assert decision["decision"] == "ready_for_final_acceptance_and_stabilization_prd"

