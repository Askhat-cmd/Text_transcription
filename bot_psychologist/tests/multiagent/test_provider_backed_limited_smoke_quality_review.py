from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_provider_backed_limited_smoke_execution as execution


def test_provider_backed_limited_smoke_quality_review() -> None:
    passed = execution.build_quality_review(
        aggregate={"provider_call_failures_count": 0, "micro_shift_present_count": 5, "high_stakes_directive_advice_count": 0},
        pilot_execution={"pilot_apply_count": 5},
    )
    assert passed["quality_status"] == "passed"
    warning = execution.build_quality_review(
        aggregate={"provider_call_failures_count": 0, "micro_shift_present_count": 2, "high_stakes_directive_advice_count": 0},
        pilot_execution={"pilot_apply_count": 5},
    )
    assert warning["quality_status"] == "warning"
