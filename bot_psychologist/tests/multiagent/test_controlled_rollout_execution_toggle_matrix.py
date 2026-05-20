from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_controlled_rollout_execution as execution  # noqa: E402


def test_controlled_rollout_execution_toggle_matrix() -> None:
    payload = execution.build_toggle_matrix()
    assert payload["ready"] is True
    matrix = payload["matrix"]
    assert matrix["force_disabled=true"] == "total disabled"
    assert matrix["normal_user"] == "never apply"

