from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import bot_agent.answer_adaptive as adaptive
from tests.phase8_runtime_support import setup_phase8_runtime


def test_onboarding_start_command_first_session(monkeypatch) -> None:
    harness = setup_phase8_runtime(
        monkeypatch,
        adaptive,
        turns_count=0,
        informational_branch_enabled=True,
    )

    result = adaptive.answer_question_adaptive(
        query="/start",
        user_id="phase8_user",
        debug=True,
    )

    assert result["status"] == "success"
    assert result["metadata"]["onboarding_start_command"] is True
    assert result["metadata"]["first_turn"] is True
    assert result["metadata"]["resolved_route"] == "contact_hold"
    assert "Neo MindBot" in result["answer"]
    assert len(harness.memory.turns) == 1
