from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_creator_live_pilot_acceptance as gate  # noqa: E402


def test_prd_046_1_36_scorecard_decision_passed() -> None:
    score = gate.build_scorecard(
        source_gate={"source_gate_passed": True},
        runtime_readiness_gate={"runtime_readiness_gate": "warning"},
        admin_controls={"admin_runtime_controls_acceptance_gate": "passed", "runtime_tab_present": True, "diagnostic_center_block_present": True, "force_disabled_toggle_present": True, "all_users_control_locked": True},
        creator_payload={"creator_live_pilot_acceptance_gate": "passed", "creator_cases_total": 7, "creator_cases_passed": 7, "creator_answer_received_count": 7, "diagnostic_center_active_for_creator_count": 7, "diagnostic_center_trace_present_count": 7},
        trace_payload={"trace_acceptance_gate": "passed"},
        rollback_payload={"rollback_gate": "warning"},
        normal_user_gate={"normal_user_no_effect_gate": "passed"},
        rag_behavior_gate={"rag_and_behavior_regression_gate": "passed"},
        trace_sanitization_gate={"trace_sanitization_gate": "passed"},
        provider_budget_gate={"provider_budget_gate": "passed"},
        no_mutation_proof={"no_mutation_proof_passed": True},
        artifact_encoding_hygiene_passed=True,
    )
    assert score["scorecard"]["final_status"] == "passed"
    assert score["scorecard"]["decision"] == "creator_live_pilot_accepted"

