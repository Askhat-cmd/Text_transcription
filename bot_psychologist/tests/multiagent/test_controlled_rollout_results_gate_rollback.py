from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_controlled_rollout_results_gate as gate  # noqa: E402


def test_controlled_rollout_results_gate_rollback() -> None:
    preflight = gate.preflight_source(Path("TO_DO_LIST/logs/PRD-046.1.31"), Path("TO_DO_LIST/reports"))
    payload = gate.build_rollback_hard_stop_gate(preflight["parsed"])
    assert payload["rollback_failure_count"] == 0
    assert payload["stale_apply_after_force_disabled_count"] == 0
    assert payload["hard_stop_triggered"] is False
    assert payload["rollback_gate_passed"] is True
