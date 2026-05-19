from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_stabilization_cleanup as cleanup


def test_stabilization_cleanup_source_gate_passed() -> None:
    preflight = cleanup.preflight_source_reports(Path("TO_DO_LIST/reports"))
    payload = cleanup.build_source_gate(preflight)
    assert preflight["ok"] is True
    assert payload["source_gate_passed"] is True
    assert payload["final_status"] == "passed"
    assert payload["decision"] == "accepted_ready_for_cleanup_stabilization"
