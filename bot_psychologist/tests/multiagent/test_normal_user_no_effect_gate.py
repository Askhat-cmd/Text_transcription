from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_final_acceptance as module


def test_normal_user_no_effect_gate_is_zeroed() -> None:
    payload = module.build_normal_user_no_effect_gate()
    assert payload["normal_user_apply_count"] == 0
    assert payload["default_off_user_path_effect_count"] == 0
    assert payload["writer_prompt_changed_for_normal_user"] is False
    assert payload["writer_contract_changed_for_normal_user"] is False
    assert payload["final_answer_changed_for_normal_user"] is False
    assert payload["synthetic_gate_only"] is True
    assert payload["final_status"] == "passed"
