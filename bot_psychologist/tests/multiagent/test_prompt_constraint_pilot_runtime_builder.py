from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.contracts.state_snapshot import StateSnapshot
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.prompt_constraint_pilot_runtime import (
    build_prompt_constraint_pilot_runtime_decision_v1,
)


def _state() -> StateSnapshot:
    return StateSnapshot("window", "clarify", "open", "I+W+", False, 0.8)


def _thread() -> ThreadState:
    return ThreadState(
        thread_id="t1",
        user_id="pilot_user_1",
        core_direction="support",
        phase="clarify",
        response_mode="reflect",
    )


def test_runtime_builder_allows_test_apply_when_all_gates_passed() -> None:
    decision = build_prompt_constraint_pilot_runtime_decision_v1(
        user_id="pilot_user_1",
        writer_prompt_replay_result={
            "quality": {
                "quality_status": "passed",
                "safety_ok": True,
                "kb_boundary_ok": True,
                "constraint_conflict_ok": True,
                "prompt_bloat_ok": True,
                "non_mutating_ok": True,
            },
            "comparison": {
                "size_delta_chars": 50,
                "size_delta_ratio": 0.05,
                "forbidden_field_hits": [],
                "conflict_rules": [],
            },
            "blocked_reasons": [],
        },
        writer_contract_pilot={
            "overlay": {
                "candidate_constraints": {
                    "depth_limit": "low",
                    "max_questions": 0,
                    "max_concepts": 1,
                    "must_do": ["validate_current_state"],
                    "must_not_do": ["do_not_analyze_deeply"],
                    "kb_usage_mode": "internal_lens_only",
                    "must_not_quote_source": True,
                }
            }
        },
        state_snapshot=_state(),
        thread_state=_thread(),
        feature_flags_snapshot={
            "PROMPT_CONSTRAINT_PILOT_ENABLED": True,
            "PROMPT_CONSTRAINT_PILOT_FORCE_DISABLED": False,
            "PROMPT_CONSTRAINT_PILOT_MODE": "test_apply",
            "PROMPT_CONSTRAINT_PILOT_ALLOWED_USER_IDS": "pilot_user_1",
            "PROMPT_CONSTRAINT_PILOT_TEST_USER_PREFIX": "pilot_",
            "PROMPT_CONSTRAINT_PILOT_MAX_PROMPT_DELTA_CHARS": "2500",
            "PROMPT_CONSTRAINT_PILOT_MAX_PROMPT_DELTA_RATIO": "0.35",
        },
    ).to_dict()

    assert decision["activation_mode"] == "test_apply"
    assert decision["apply_to_writer_prompt"] is True
    assert decision["rollback_active"] is False
    assert decision["eligible_user"] is True

