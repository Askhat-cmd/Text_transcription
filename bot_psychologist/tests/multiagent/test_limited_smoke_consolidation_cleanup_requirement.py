from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_limited_smoke_consolidation as gate


def test_limited_smoke_consolidation_cleanup_requirement() -> None:
    payload = gate.build_future_cleanup_stabilization_requirement()
    assert payload["future_cleanup_stabilization_requirement_created"] is True
    assert payload["cleanup_now"] is False
    assert len(payload["zones"]) == 4

