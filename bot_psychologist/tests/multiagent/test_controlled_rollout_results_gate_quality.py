from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_controlled_rollout_results_gate as gate  # noqa: E402


def test_controlled_rollout_results_gate_quality() -> None:
    preflight = gate.preflight_source(Path("TO_DO_LIST/logs/PRD-046.1.31"), Path("TO_DO_LIST/reports"))
    payload = gate.build_quality_micro_shift_gate(preflight["parsed"])
    assert payload["candidate_weaker_than_baseline_count"] == 0
    assert payload["hard_fail_count"] == 0
    assert payload["response_quality_regression_count"] == 0
    assert payload["quality_micro_shift_gate_passed"] is True
