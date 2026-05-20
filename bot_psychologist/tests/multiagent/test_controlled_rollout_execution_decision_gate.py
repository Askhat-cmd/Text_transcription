from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_controlled_rollout_execution as execution  # noqa: E402


def test_controlled_rollout_execution_decision_gate() -> None:
    decision = execution.build_decision(
        source_gate={"source_gate_passed": True},
        execution_manifest={"execution_performed": True, "target_operator_count": 3},
        execution_results={"scenario_count": 12, "provider_calls_total": 12},
        budget={"provider_budget_gate_passed": True},
        normal_user={"normal_user_control_count": 3, "normal_user_apply_count": 0, "normal_user_provider_calls": 0},
        quality={"gate_passed": True},
        safety={"gate_passed": True},
        trace={"gate_passed": True},
        rollback={"gate_passed": True},
        hard_stop={"hard_stop_triggered": False},
        botdb={"gate_passed": True},
        no_mutation={"no_mutation_proof_passed": True},
        hygiene={"gate_passed": True},
        docs_sync={"docs_synced": True},
    )
    assert decision["final_status"] == "passed"
    assert decision["decision"] == "controlled_rollout_execution_passed_ready_for_results_gate"

