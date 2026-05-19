from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_controlled_rollout_planning as planning


def test_controlled_rollout_planning_hard_stops() -> None:
    payload = planning.build_hard_stop_criteria()
    assert payload["ready"] is True
    assert "provider budget exceeded" in payload["hard_stops"]
    assert "runtime defaults changed" in payload["hard_stops"]
