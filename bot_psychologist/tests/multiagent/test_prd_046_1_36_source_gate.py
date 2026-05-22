from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_creator_live_pilot_acceptance as gate  # noqa: E402


def test_prd_046_1_36_source_gate_reads_hf4_inputs() -> None:
    preflight = gate.preflight_source(Path(".").resolve())
    payload = gate.build_source_gate(preflight)
    assert payload["schema_version"] == "diagnostic_center_creator_live_pilot_source_gate_v1"
    assert "source_gate_passed" in payload
    assert payload["checks"]["hf4_final_status_passed"] is True

