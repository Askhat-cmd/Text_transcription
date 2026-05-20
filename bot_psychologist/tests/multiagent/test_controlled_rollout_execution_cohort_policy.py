from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_controlled_rollout_execution as execution  # noqa: E402


def test_controlled_rollout_execution_cohort_policy() -> None:
    preflight = execution.preflight_source(
        reports_dir=Path("TO_DO_LIST/reports"),
        docs_dir=Path("docs"),
        source_dir=Path("TO_DO_LIST/logs/PRD-046.1.30"),
    )
    payload = execution.build_cohort_policy(preflight)
    assert payload["ready"] is True
    assert payload["max_target_operator_count"] <= 3
    assert payload["normal_user_activation_allowed"] is False

