from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_controlled_cohort_expansion as gate


def test_controlled_cohort_expansion_decision_gate_passed() -> None:
    decision_gate, _ = gate.build_decision_gate(
        source_gate={"source_gate_passed": True},
        botdb_preflight={"botdb_preflight_passed": True},
        cohort_policy={"cohort_policy_passed": True},
        provider_execution_evidence={"target_user_count": 3, "scenario_count": 12},
        provider_budget_gate={"provider_budget_gate_passed": True},
        normal_user_no_effect_gate={"normal_user_no_effect_gate_passed": True},
        quality_micro_shift_gate={"quality_micro_shift_gate_passed": True, "micro_shift_present_rate": 1.0},
        safety_kb_boundary_gate={"safety_kb_boundary_gate_passed": True},
        trace_provider_sanitization_gate={"trace_provider_sanitization_gate_passed": True},
        rollback_gate={"rollback_gate_passed": True},
        botdb_stability_gate={"botdb_stability_gate_passed": True},
        hard_stop_gate={"hard_stop_triggered": False},
        no_mutation_proof={"no_mutation_passed": True},
        artifact_encoding_hygiene_passed=True,
    )
    assert decision_gate["final_status"] == "passed"
    assert decision_gate["decision"] == "ready_for_final_acceptance_and_stabilization_prd"


def test_controlled_cohort_expansion_decision_gate_blocked() -> None:
    decision_gate, _ = gate.build_decision_gate(
        source_gate={"source_gate_passed": False},
        botdb_preflight={"botdb_preflight_passed": False},
        cohort_policy={"cohort_policy_passed": False},
        provider_execution_evidence={"target_user_count": 2, "scenario_count": 8},
        provider_budget_gate={"provider_budget_gate_passed": False},
        normal_user_no_effect_gate={"normal_user_no_effect_gate_passed": False},
        quality_micro_shift_gate={"quality_micro_shift_gate_passed": False, "micro_shift_present_rate": 0.4},
        safety_kb_boundary_gate={"safety_kb_boundary_gate_passed": False},
        trace_provider_sanitization_gate={"trace_provider_sanitization_gate_passed": False},
        rollback_gate={"rollback_gate_passed": False},
        botdb_stability_gate={"botdb_stability_gate_passed": False},
        hard_stop_gate={"hard_stop_triggered": True},
        no_mutation_proof={"no_mutation_passed": False},
        artifact_encoding_hygiene_passed=False,
    )
    assert decision_gate["final_status"] == "blocked"
    assert decision_gate["decision"] == "blocked_requires_hotfix"

