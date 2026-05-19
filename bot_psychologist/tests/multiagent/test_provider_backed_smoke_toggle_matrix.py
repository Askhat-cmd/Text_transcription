from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_provider_backed_smoke_readiness as readiness


def test_provider_backed_smoke_toggle_matrix_has_conservative_default() -> None:
    payload = readiness.build_toggle_matrix()
    baseline = payload["baseline_conservative_state"]
    planned = payload["planned_next_execution_state"]
    rollback = payload["post_execution_rollback_state"]
    assert baseline["PROMPT_CONSTRAINT_PILOT_FORCE_DISABLED"] == "true"
    assert baseline["PROMPT_CONSTRAINT_PILOT_ENABLED"] == "false"
    assert planned["PROMPT_CONSTRAINT_PILOT_MODE"] == "provider_backed_limited_smoke"
    assert rollback["PROMPT_CONSTRAINT_PILOT_MODE"] == "shadow"
