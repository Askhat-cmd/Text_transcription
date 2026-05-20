from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_controlled_rollout_results_gate as gate  # noqa: E402


def test_controlled_rollout_results_gate_normal_user_no_effect() -> None:
    preflight = gate.preflight_source(Path("TO_DO_LIST/logs/PRD-046.1.31"), Path("TO_DO_LIST/reports"))
    payload = gate.build_normal_user_no_effect_gate(preflight["parsed"])
    assert payload["normal_user_controls_total"] >= 3
    assert payload["normal_user_apply_count"] == 0
    assert payload["normal_user_provider_calls_total"] == 0
    assert payload["normal_user_no_effect_passed"] is True
