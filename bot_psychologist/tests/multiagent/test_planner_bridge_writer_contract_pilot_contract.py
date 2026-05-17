from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.contracts.planner_bridge_writer_contract_pilot_v1 import (
    PlannerBridgeWriterContractPilotOverlay,
)


def test_writer_contract_pilot_contract_enforces_non_mutating_guardrails() -> None:
    payload = PlannerBridgeWriterContractPilotOverlay.from_dict(
        {
            "activation_mode": "active",
            "apply_to_writer_contract": True,
            "apply_to_writer_prompt": True,
            "apply_to_final_answer": True,
            "guardrails": {
                "writer_contract_changed": True,
                "writer_prompt_changed": True,
                "final_answer_changed": True,
                "provider_called": True,
            },
            "merge_policy": {"mode": "active_merge"},
        }
    ).to_dict()
    assert payload["activation_mode"] == "pilot_shadow_only"
    assert payload["apply_to_writer_contract"] is False
    assert payload["apply_to_writer_prompt"] is False
    assert payload["apply_to_final_answer"] is False
    assert payload["merge_policy"]["mode"] == "non_mutating_compare_only"
