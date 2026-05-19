from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_second_provider_backed_smoke as gate


def test_second_provider_backed_smoke_decision_gate_continue_candidate() -> None:
    execution_manifest = gate.build_execution_manifest(scenarios_count=6)
    execution = {"provider_calls_performed": 6}
    decision_gate, _ = gate.build_decision_gate(
        source_gate={"source_gate_passed": True},
        botdb_live_preflight={"botdb_live_preflight_passed": True},
        rollback_precheck={"rollback_precheck_passed": True},
        execution_manifest=execution_manifest,
        provider_preflight={"provider_availability_preflight_passed": True},
        execution=execution,
        provider_budget_gate={"provider_budget_gate_passed": True},
        normal_user_no_effect_gate={"normal_user_no_effect_gate_passed": True, "diagnostic_center_apply_count": 0, "provider_call_count": 0},
        quality_micro_shift_gate={"quality_micro_shift_gate_passed": True},
        safety_kb_boundary_gate={"safety_kb_boundary_gate_passed": True},
        trace_sanitization_gate={"trace_sanitization_gate_passed": True},
        rollback_postcheck={"rollback_postcheck_passed": True},
        botdb_stability_gate={"botdb_stability_gate_passed": True},
        no_mutation_proof={"no_mutation_passed": True},
        artifact_encoding_hygiene_passed=True,
    )
    assert decision_gate["final_status"] == "passed"
    assert decision_gate["decision"] == "continue_limited_candidate"
