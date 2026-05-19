from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_controlled_cohort_expansion as gate


def test_controlled_cohort_expansion_normal_user_no_effect_gate() -> None:
    payload = gate.build_normal_user_no_effect_gate()
    assert payload["normal_user_no_effect_gate_passed"] is True
    assert payload["normal_user_apply_count"] == 0
    assert payload["normal_user_provider_calls"] == 0
    assert payload["normal_user_controls_total"] >= 3

