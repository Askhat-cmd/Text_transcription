from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.contracts.planner_bridge_compliance_v1 import (
    PlannerBridgeComplianceShadow,
)


def test_compliance_contract_enforces_shadow_compare_only_guardrails() -> None:
    payload = PlannerBridgeComplianceShadow.from_dict(
        {
            "activation_mode": "active",
            "apply_to_writer": True,
            "apply_to_writer_contract": True,
            "writer_prompt_changed": True,
            "final_answer_changed": True,
            "compatibility": {"overall_status": "compatible"},
        }
    ).to_dict()
    assert payload["activation_mode"] == "shadow_compare_only"
    assert payload["apply_to_writer"] is False
    assert payload["apply_to_writer_contract"] is False
    assert payload["writer_prompt_changed"] is False
    assert payload["final_answer_changed"] is False
    assert payload["trace"]["source"] == "shadow_compare_only"

