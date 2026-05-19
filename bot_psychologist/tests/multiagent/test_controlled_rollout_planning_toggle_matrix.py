from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_controlled_rollout_planning as planning


def test_controlled_rollout_planning_toggle_matrix() -> None:
    payload = planning.build_toggle_matrix()
    assert payload["ready"] is True
    assert payload["matrix"]["force_disabled=true"] == "total disabled"
    assert payload["matrix"]["normal_user"] == "never apply"
