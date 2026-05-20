from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_controlled_rollout_execution as execution  # noqa: E402


def test_controlled_rollout_execution_normal_user_no_effect() -> None:
    payload = execution.build_normal_user_no_effect_gate()
    assert payload["gate_passed"] is True
    assert payload["normal_user_control_count"] >= 3
    assert payload["normal_user_apply_count"] == 0
    assert payload["normal_user_provider_calls"] == 0

