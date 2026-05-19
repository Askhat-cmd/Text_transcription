from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_limited_smoke_consolidation as gate


def test_limited_smoke_consolidation_expansion_readiness() -> None:
    payload = gate.build_controlled_cohort_expansion_readiness(
        passed=True,
        decision="ready_for_controlled_cohort_expansion_prd",
    )
    assert payload["controlled_cohort_expansion_readiness_ready"] is True
    assert payload["max_target_users"] == 3
    assert payload["provider_budget_limit_max"] == 12

