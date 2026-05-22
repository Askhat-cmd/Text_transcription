from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_final_completion_gate as gate  # noqa: E402


def test_prd_046_1_37_source_gate_reads_prd_046_1_36_inputs() -> None:
    preflight = gate.preflight_source(Path(".").resolve())
    payload = gate.build_source_gate(preflight)
    assert payload["schema_version"] == "diagnostic_center_final_source_gate_v1"
    assert payload["checks"]["final_status_passed"] is True
    assert payload["checks"]["decision_ok"] is True
