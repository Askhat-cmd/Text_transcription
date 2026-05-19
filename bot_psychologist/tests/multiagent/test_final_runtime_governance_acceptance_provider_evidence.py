from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_final_runtime_governance_acceptance as gate


def test_final_runtime_governance_acceptance_provider_evidence() -> None:
    preflight = gate.preflight_source_chain(
        [
            Path("TO_DO_LIST/logs/PRD-046.1.23"),
            Path("TO_DO_LIST/logs/PRD-046.1.24"),
            Path("TO_DO_LIST/logs/PRD-046.1.25"),
            Path("TO_DO_LIST/logs/PRD-046.1.26"),
            Path("TO_DO_LIST/logs/PRD-046.1.27"),
        ],
        Path("TO_DO_LIST/reports"),
        Path("."),
    )
    payload = gate.build_cumulative_provider_evidence(preflight["parsed"])
    assert payload["provider_backed_cycles_total"] == 3
    assert payload["provider_scenarios_total"] >= 23
    assert payload["provider_calls_total"] >= 23
    assert payload["cumulative_provider_evidence_gate_passed"] is True

