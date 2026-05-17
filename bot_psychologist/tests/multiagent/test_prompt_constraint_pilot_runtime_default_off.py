from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.contracts.state_snapshot import StateSnapshot
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.prompt_constraint_pilot_runtime import (
    build_prompt_constraint_pilot_runtime_decision_v1,
)


def test_default_off_disables_apply() -> None:
    decision = build_prompt_constraint_pilot_runtime_decision_v1(
        user_id="pilot_u",
        writer_prompt_replay_result={},
        writer_contract_pilot={},
        state_snapshot=StateSnapshot("window", "clarify", "open", "I+W+", False, 0.8),
        thread_state=ThreadState(
            thread_id="t1",
            user_id="pilot_u",
            core_direction="support",
            phase="clarify",
        ),
        feature_flags_snapshot={
            "PROMPT_CONSTRAINT_PILOT_ENABLED": False,
            "PROMPT_CONSTRAINT_PILOT_FORCE_DISABLED": False,
            "PROMPT_CONSTRAINT_PILOT_MODE": "test_apply",
            "PROMPT_CONSTRAINT_PILOT_ALLOWED_USER_IDS": "pilot_u",
            "PROMPT_CONSTRAINT_PILOT_TEST_USER_PREFIX": "pilot_",
        },
    ).to_dict()
    assert decision["activation_mode"] == "disabled"
    assert decision["apply_to_writer_prompt"] is False
    assert "feature_flag_disabled" in decision["blocked_reasons"]

