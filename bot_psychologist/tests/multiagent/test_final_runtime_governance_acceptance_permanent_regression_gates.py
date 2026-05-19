from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_final_runtime_governance_acceptance as gate


def test_final_runtime_governance_acceptance_permanent_regression_gates() -> None:
    payload = gate.build_permanent_regression_gates()
    assert payload["permanent_regression_gates_report_ready"] is True
    assert "normal-user no-effect gate" in payload["permanent_gate_families"]
    assert "temporary transition fixtures" in payload["candidate_archive_families_after_cleanup"]

