from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_controlled_rollout_planning as planning


def test_controlled_rollout_planning_decision_gate() -> None:
    source_gate = {
        "source_gate_passed": True,
        "runtime_map_gate_passed": True,
        "eval_harness_gate_passed": True,
    }
    cohort = planning.build_cohort_policy()
    toggle = planning.build_toggle_matrix()
    preflight = planning.build_preflight_gates()
    hard_stops = planning.build_hard_stop_criteria()
    monitoring = planning.build_monitoring_plan()
    rollback = planning.build_rollback_plan()
    evidence = planning.build_evidence_capture_plan()
    normal_user = planning.build_normal_user_no_effect_plan()
    no_mutation = {
        "no_mutation_proof_passed": True,
        "production_data_mutated": False,
    }
    docs_sync = {"docs_synced": True}
    decision, scorecard = planning.build_decision_and_scorecard(
        source_gate=source_gate,
        cohort_policy=cohort,
        toggle_matrix=toggle,
        preflight_gates=preflight,
        hard_stop_criteria=hard_stops,
        monitoring_plan=monitoring,
        rollback_plan=rollback,
        evidence_capture_plan=evidence,
        normal_user_no_effect_plan=normal_user,
        no_mutation_proof=no_mutation,
        artifact_hygiene_passed=True,
        docs_sync=docs_sync,
    )
    assert decision["final_status"] == "passed"
    assert decision["decision"] == "ready_for_controlled_rollout_execution_prd"
    assert scorecard["final_status"] == "passed"
