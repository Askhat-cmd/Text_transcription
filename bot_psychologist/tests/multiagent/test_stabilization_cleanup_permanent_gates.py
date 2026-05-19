from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_stabilization_cleanup as cleanup


def test_stabilization_cleanup_permanent_gates_revalidated() -> None:
    payload = cleanup.revalidate_permanent_gates(Path("."))
    assert payload["permanent_gate_revalidation_passed"] is True
