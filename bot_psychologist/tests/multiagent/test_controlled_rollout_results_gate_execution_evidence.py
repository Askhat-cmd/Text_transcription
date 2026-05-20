from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_controlled_rollout_results_gate as gate  # noqa: E402


def test_controlled_rollout_results_gate_execution_evidence() -> None:
    preflight = gate.preflight_source(Path("TO_DO_LIST/logs/PRD-046.1.31"), Path("TO_DO_LIST/reports"))
    source_gate = gate.build_source_gate(preflight)
    payload = gate.build_execution_evidence_consolidation(source_gate)
    assert payload["new_execution_performed"] is False
    assert payload["provider_called_by_results_gate"] is False
    assert payload["execution_evidence_consolidation_passed"] is True
