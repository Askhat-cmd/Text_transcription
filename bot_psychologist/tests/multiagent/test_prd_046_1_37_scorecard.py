from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_final_completion_gate as gate  # noqa: E402


def test_prd_046_1_37_scorecard_decision_completed() -> None:
    scorecard, decision = gate.build_final_scorecard(
        source_gate={"source_gate_passed": True},
        evidence_audit={"gate": "passed"},
        runtime_gate={"runtime_readiness_final_gate": "passed_with_warning"},
        live_smoke={
            "gate": "passed",
            "actual_live_cases_total": 5,
            "actual_live_cases_passed": 5,
            "diagnostic_center_active_for_creator_count": 5,
            "diagnostic_center_trace_present_count": 5,
        },
        admin_gate={"admin_runtime_controls_final_gate": "passed_with_warning"},
        rollback_gate={"rollback_hard_stop_final_gate": "passed_with_warning"},
        normal_gate={
            "normal_user_final_no_effect_gate": "passed",
            "diagnostic_center_live_authority_applied": False,
        },
        rag_gate={"rag_behavior_final_regression_gate": "passed"},
        trace_gate={"trace_sanitization_final_gate": "passed"},
        budget_gate={"provider_budget_final_gate": "passed"},
        no_mutation={"no_mutation_final_proof_passed": True},
        artifact_encoding_hygiene_passed=True,
    )
    assert scorecard["final_status"] == "completed"
    assert scorecard["decision"] == gate.DECISION_COMPLETED
    assert decision["decision"] == gate.DECISION_COMPLETED
