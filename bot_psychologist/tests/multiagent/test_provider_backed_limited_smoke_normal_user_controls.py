from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_provider_backed_limited_smoke_execution as execution


def test_provider_backed_limited_smoke_normal_user_controls() -> None:
    controls, trace = execution.build_normal_user_controls()
    assert controls["normal_user_control_count"] >= 2
    assert controls["normal_user_apply_count"] == 0
    assert controls["normal_user_provider_apply_count"] == 0
    assert len(trace["samples"]) >= 2
