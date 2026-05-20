from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_limited_activation_readiness as gate  # noqa: E402


def test_limited_activation_readiness_rollback_hard_stop_gate() -> None:
    payload = gate.build_rollback_hard_stop_gate()
    assert payload["rollback_hard_stop_gate_passed"] is True
    assert payload["rollback_controls_present"] is True
    assert payload["hard_stop_criteria_complete"] is True

