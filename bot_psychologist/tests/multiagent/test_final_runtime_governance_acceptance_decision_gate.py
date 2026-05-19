from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_final_runtime_governance_acceptance as gate


def test_final_runtime_governance_acceptance_decision_gate_passed() -> None:
    boundary_decision, next_prd, risk_register, scorecard = gate.build_decision_gate(
        source_chain={"source_chain_gate_passed": True, "source_chain_complete": True},
        provider_evidence={"cumulative_provider_evidence_gate_passed": True, "provider_backed_cycles_total": 3, "provider_scenarios_total": 23, "provider_budget_violation_count": 0},
        normal_user_no_effect={"normal_user_no_effect_gate_passed": True, "normal_user_apply_count_total": 0, "normal_user_provider_calls_total": 0},
        rollback_hard_stop={"rollback_hard_stop_gate_passed": True, "rollback_failure_count_total": 0, "hard_stop_ignored_count": 0},
        safety_kb_boundary={"safety_kb_boundary_gate_passed": True},
        trace_provider_sanitization={"trace_provider_sanitization_gate_passed": True},
        botdb_stability={"botdb_stability_gate_passed": True},
        quality_micro_shift={"quality_micro_shift_gate_passed": True},
        permanent_regression_gates={"permanent_regression_gates_report_ready": True},
        runtime_governance_boundaries={"runtime_governance_boundary_decision_ready": True},
        cleanup_stabilization_readiness={"cleanup_stabilization_readiness_ready": True},
        no_mutation_proof={"no_mutation_proof_passed": True},
        artifact_hygiene={"artifact_encoding_hygiene_passed": True},
        docs_sync={"docs_synced": True},
    )
    assert boundary_decision["final_status"] == "passed"
    assert boundary_decision["decision"] == "accepted_ready_for_cleanup_stabilization"
    assert next_prd["recommended_next_prd"].startswith("PRD-046.1.29")
    assert risk_register["risk_register_has_blockers"] is False
    assert scorecard["final_status"] == "passed"

