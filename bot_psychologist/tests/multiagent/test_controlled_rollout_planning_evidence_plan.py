from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_controlled_rollout_planning as planning


def test_controlled_rollout_planning_evidence_plan() -> None:
    payload = planning.build_evidence_capture_plan()
    assert payload["ready"] is True
    assert "execution_manifest" in payload["required_artifacts"]
    assert "next_prd_recommendation" in payload["required_artifacts"]
