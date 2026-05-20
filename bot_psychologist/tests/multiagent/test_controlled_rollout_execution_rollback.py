from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_controlled_rollout_execution as execution  # noqa: E402


def test_controlled_rollout_execution_rollback() -> None:
    payload = execution.build_rollback_proof()
    assert payload["gate_passed"] is True
    assert payload["rollback_precheck_passed"] is True
    assert payload["rollback_postcheck_passed"] is True

