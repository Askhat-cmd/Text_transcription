from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_second_provider_backed_smoke as gate


def test_second_provider_backed_smoke_normal_user_no_effect_gate() -> None:
    payload = gate.build_normal_user_no_effect_gate()
    assert payload["normal_user_control_count"] == 2
    assert payload["diagnostic_center_apply_count"] == 0
    assert payload["provider_call_count"] == 0
    assert payload["normal_user_no_effect_gate_passed"] is True
