from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_final_runtime_governance_acceptance as gate


def test_final_runtime_governance_acceptance_quality_micro_shift() -> None:
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
    provider_evidence = gate.build_cumulative_provider_evidence(preflight["parsed"])
    payload = gate.build_quality_micro_shift_gate(preflight["parsed"], provider_evidence)
    assert payload["provider_scenarios_total"] >= 23
    assert payload["micro_shift_present_count_total"] >= 19
    assert payload["quality_micro_shift_gate_passed"] is True

