from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_final_acceptance as module


def test_prompt_constraint_baseline_gate_passed_for_defaults() -> None:
    payload = module.build_prompt_constraint_conservative_baseline_gate(Path(".").resolve())
    assert payload["PROMPT_CONSTRAINT_PILOT_ENABLED_default"] is False
    assert payload["PROMPT_CONSTRAINT_PILOT_FORCE_DISABLED_default"] is True
    assert payload["PROMPT_CONSTRAINT_PILOT_ALLOWED_USER_IDS_default"] == ""
    assert payload["PROMPT_CONSTRAINT_PILOT_TEST_USER_PREFIX_default"] == "pilot_"
    assert payload["force_disabled_priority_preserved"] is True
    assert payload["final_status"] == "passed"
