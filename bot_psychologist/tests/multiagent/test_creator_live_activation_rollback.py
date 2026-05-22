from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_creator_live_activation as gate  # noqa: E402


def test_rollback_kill_switch_gate() -> None:
    payload = gate.build_rollback_kill_switch_gate()
    assert payload["rollback_kill_switch_gate_passed"] is True
    assert payload["stale_apply_after_force_disabled_count"] == 0
