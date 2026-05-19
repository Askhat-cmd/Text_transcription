from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_controlled_cohort_expansion as gate


def test_controlled_cohort_expansion_rollback_gate() -> None:
    payload = gate.build_rollback_gate()
    assert payload["rollback_gate_passed"] is True
    assert payload["rollback_precheck_passed"] is True
    assert payload["rollback_postcheck_passed"] is True
    assert payload["stale_apply_after_force_disabled_count"] == 0

