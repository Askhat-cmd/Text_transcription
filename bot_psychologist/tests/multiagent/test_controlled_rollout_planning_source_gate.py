from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_controlled_rollout_planning as planning


def test_controlled_rollout_planning_source_gate() -> None:
    preflight = planning.preflight(Path("TO_DO_LIST/reports"), Path("docs"))
    payload = planning.build_source_gate(preflight)
    assert preflight["ok"] is True
    assert payload["source_gate_passed"] is True
