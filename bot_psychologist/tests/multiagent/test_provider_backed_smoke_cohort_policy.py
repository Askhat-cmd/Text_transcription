from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_provider_backed_smoke_readiness as readiness


def test_provider_backed_smoke_cohort_policy_is_limited() -> None:
    payload = readiness.build_cohort_policy()
    assert payload["target_user_count"] == 1
    assert payload["allowed_user_ids"] == ["pilot_runtime_operator_001"]
    assert payload["normal_users_allowed"] is False
    assert payload["broad_rollout_allowed"] is False
