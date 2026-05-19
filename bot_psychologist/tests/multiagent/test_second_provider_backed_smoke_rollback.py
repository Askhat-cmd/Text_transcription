from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_second_provider_backed_smoke as gate


def test_second_provider_backed_smoke_rollback_gates() -> None:
    pre = gate.build_rollback_precheck()
    post = gate.build_rollback_postcheck()
    assert pre["rollback_precheck_passed"] is True
    assert post["rollback_postcheck_passed"] is True
    assert post["stale_apply_after_force_disabled_count"] == 0
