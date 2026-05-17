from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.contracts.prompt_constraint_pilot_runtime_v1 import (
    PromptConstraintPilotRuntimeDecision,
)


def test_runtime_decision_enforces_invariants() -> None:
    decision = PromptConstraintPilotRuntimeDecision(
        activation_mode="test_apply",
        apply_to_writer_prompt=True,
        apply_to_writer_contract=True,
        apply_to_final_answer=True,
        rollback_active=False,
    ).to_dict()
    assert decision["activation_mode"] == "test_apply"
    assert decision["apply_to_writer_prompt"] is True
    assert decision["apply_to_writer_contract"] is False
    assert decision["apply_to_final_answer"] is False


def test_runtime_decision_rollback_forces_disabled() -> None:
    decision = PromptConstraintPilotRuntimeDecision(
        activation_mode="test_apply",
        apply_to_writer_prompt=True,
        rollback_active=True,
    ).to_dict()
    assert decision["activation_mode"] == "disabled"
    assert decision["apply_to_writer_prompt"] is False
    assert decision["rollback_active"] is True

