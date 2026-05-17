from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.contracts.state_snapshot import StateSnapshot
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.prompt_constraint_pilot_runtime import (
    build_prompt_constraint_pilot_runtime_decision_v1,
)


def test_safety_case_blocks_unsafe_constraints() -> None:
    decision = build_prompt_constraint_pilot_runtime_decision_v1(
        user_id="pilot_safe_1",
        writer_prompt_replay_result={
            "quality": {
                "quality_status": "passed",
                "safety_ok": True,
                "kb_boundary_ok": True,
                "constraint_conflict_ok": True,
                "prompt_bloat_ok": True,
                "non_mutating_ok": True,
            },
            "comparison": {"forbidden_field_hits": [], "conflict_rules": []},
            "blocked_reasons": [],
        },
        writer_contract_pilot={
            "overlay": {
                "candidate_constraints": {
                    "depth_limit": "medium",
                    "max_questions": 2,
                    "max_concepts": 3,
                }
            }
        },
        state_snapshot=StateSnapshot("hyper", "contact", "defensive", "I-W+", True, 0.9),
        thread_state=ThreadState(
            thread_id="t1",
            user_id="pilot_safe_1",
            core_direction="safety",
            phase="stabilize",
            safety_active=True,
        ),
        feature_flags_snapshot={
            "PROMPT_CONSTRAINT_PILOT_ENABLED": True,
            "PROMPT_CONSTRAINT_PILOT_FORCE_DISABLED": False,
            "PROMPT_CONSTRAINT_PILOT_MODE": "test_apply",
            "PROMPT_CONSTRAINT_PILOT_ALLOWED_USER_IDS": "pilot_safe_1",
            "PROMPT_CONSTRAINT_PILOT_TEST_USER_PREFIX": "pilot_",
        },
    ).to_dict()
    assert decision["activation_mode"] == "shadow_only"
    assert decision["apply_to_writer_prompt"] is False
    assert "unsafe_constraints_for_current_state" in decision["blocked_reasons"]

