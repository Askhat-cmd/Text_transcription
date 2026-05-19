from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_controlled_rollout_planning as planning


def test_controlled_rollout_planning_normal_user_no_effect() -> None:
    payload = planning.build_normal_user_no_effect_plan()
    assert payload["normal_user_activation_allowed"] is False
    assert payload["normal_user_apply_allowed"] is False
    assert payload["ready"] is True
