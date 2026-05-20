from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_controlled_rollout_execution as execution  # noqa: E402


def test_controlled_rollout_execution_quality_micro_shift() -> None:
    payload = execution.build_quality_micro_shift_gate(execution_results={"scenario_count": 12})
    assert payload["gate_passed"] is True
    assert payload["scenario_count"] >= 12
    assert payload["micro_shift_present_rate"] >= 0.9

