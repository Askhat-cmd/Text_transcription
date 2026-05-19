from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_limited_smoke_consolidation as gate


def test_limited_smoke_consolidation_decision_gate() -> None:
    decision_gate, _ = gate.build_decision_gate(
        source_gate={"source_gate_passed": True},
        cumulative_provider_evidence={"cumulative_provider_evidence_passed": True},
        normal_user_no_effect_cumulative={"normal_user_no_effect_cumulative_passed": True},
        rollback_cumulative={"rollback_failures_total": 0},
        safety_kb_boundary_cumulative={"safety_kb_boundary_cumulative_passed": True},
        trace_provider_sanitization_cumulative={"trace_provider_sanitization_cumulative_passed": True},
        botdb_stability_trend={"botdb_stability_gate": "passed"},
        quality_micro_shift_cumulative={"quality_micro_shift_gate": "passed", "micro_shift_present_count_total": 11, "quality_regression_count_total": 0},
        no_mutation_proof={"no_mutation_gate": "passed"},
        artifact_encoding_hygiene_passed=True,
    )
    assert decision_gate["final_status"] == "passed"
    assert decision_gate["decision"] == "ready_for_controlled_cohort_expansion_prd"

