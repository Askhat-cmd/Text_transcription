from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import prompt_constraint_production_limited_results_gate as gate


REQUIRED_RISK_IDS = {
    "single_synthetic_operator_target_only",
    "limited_real_user_evidence",
    "operator_error_risk",
    "rollback_drift_risk",
    "trace_leakage_risk",
    "long_context_prompt_bloat_risk",
    "future_real_user_variability",
    "eval_harness_accumulation_cleanup_risk",
}


def test_risk_register_contains_required_risks() -> None:
    risks = gate.build_default_risk_register()
    risk_ids = {item["risk_id"] for item in risks}
    assert REQUIRED_RISK_IDS.issubset(risk_ids)


def test_blocking_risk_blocks_ready_for_stabilization_cleanup() -> None:
    preflight = gate.preflight(Path("TO_DO_LIST/logs/PRD-046.1.13"))
    assert preflight["ok"] is True

    risks = gate.build_default_risk_register()
    risks[0] = {**risks[0], "status": "blocking", "blocks_stabilization": True}

    _, _, _, _, _, risk_register, decision_gate, _, _ = gate.execute_results_gate(
        strict=True,
        parsed=preflight["parsed"],
        risk_entries=risks,
    )
    assert risk_register["risk_register_has_blockers"] is True
    assert decision_gate["decision"] != "ready_for_stabilization_cleanup"
