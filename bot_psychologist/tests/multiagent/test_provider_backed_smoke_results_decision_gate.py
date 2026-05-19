from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_provider_backed_smoke_results_gate as gate


def test_provider_backed_smoke_results_decision_gate_continue_candidate() -> None:
    repo_root = Path(".").resolve()
    preflight = gate.preflight_source(Path("TO_DO_LIST/logs/PRD-046.1.23"), Path("TO_DO_LIST/reports"))
    tracked, hash_before = gate.tracked_hashes(repo_root)
    hash_after = {name: gate._sha256(path) for name, path in tracked.items()}  # noqa: SLF001
    generated = gate.build_no_mutation_proof(hash_before=hash_before, hash_after=hash_after)

    source_gate = gate.build_source_gate(preflight["parsed"], True)
    execution = gate.build_provider_execution_evidence_review(preflight["parsed"])
    budget = gate.build_provider_budget_review(preflight["parsed"])
    normal_user = gate.build_normal_user_no_effect_review(preflight["parsed"])
    quality = gate.build_quality_consolidation_review(preflight["parsed"])
    safety = gate.build_safety_kb_boundary_consolidation(preflight["parsed"])
    provider_sanitize = gate.build_provider_output_sanitization_consolidation(preflight["parsed"])
    trace = gate.build_trace_sanitization_consolidation(preflight["parsed"])
    rollback = gate.build_rollback_evidence_review(preflight["parsed"])
    botdb = gate.build_botdb_stability_review(preflight["parsed"])
    no_mutation = gate.build_no_mutation_review(preflight["parsed"], generated)
    hard_stop_absence = gate.build_hard_stop_absence_review(
        parsed=preflight["parsed"],
        provider_budget_review=budget,
        normal_user_no_effect_review=normal_user,
        safety_consolidation=safety,
        provider_output_sanitization=provider_sanitize,
        trace_sanitization=trace,
        rollback_evidence=rollback,
        botdb_stability=botdb,
        no_mutation_review=no_mutation,
    )
    risk = gate.build_risk_register()

    decision_gate, _ = gate.build_decision_gate(
        source_gate=source_gate,
        provider_execution_evidence_review=execution,
        provider_budget_review=budget,
        normal_user_no_effect_review=normal_user,
        quality_consolidation_review=quality,
        safety_kb_boundary_consolidation=safety,
        provider_output_sanitization_consolidation=provider_sanitize,
        trace_sanitization_consolidation=trace,
        rollback_evidence_review=rollback,
        botdb_stability_review=botdb,
        hard_stop_absence_review=hard_stop_absence,
        no_mutation_review=no_mutation,
        risk_register=risk,
    )
    assert decision_gate["decision"] == "continue_limited_candidate"
    assert decision_gate["final_status"] == "passed"

