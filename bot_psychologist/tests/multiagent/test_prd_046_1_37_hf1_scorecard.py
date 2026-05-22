from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_diagnostic_center_final_completion_hf1 as runner  # noqa: E402


def test_prd_046_1_37_hf1_scorecard_pass_logic() -> None:
    scorecard = runner._build_final_scorecard(  # noqa: SLF001
        source_gate={"source_gate": "passed"},
        docs_correction={"docs_state_pre_rerun_correction": "passed"},
        endpoint_matrix={"endpoint_matrix_probe": "passed"},
        timeout_diagnosis={"adaptive_timeout_diagnosis": "passed"},
        latency_profile={"latency_profile_gate": "passed", "recommended_runner_timeout_sec": 60},
        actual_live_smoke={"actual_live_creator_smoke_gate": "passed", "actual_live_cases_total": 5, "actual_live_cases_passed": 5},
        trace_acceptance={"trace_acceptance_gate": "passed"},
        rollback_live={"rollback_hard_stop_live_gate": "passed_with_warning"},
        normal_user_live={"normal_user_live_no_effect_gate": "passed"},
        rag_gate={"rag_behavior_regression_gate": "passed"},
        provider_budget={"provider_budget_gate": "passed"},
        no_mutation={"no_mutation_proof": "passed"},
        artifact_encoding_hygiene=True,
    )
    assert scorecard["final_status"] == "passed"
    assert scorecard["decision"] == runner.DECISION_COMPLETED


def test_prd_046_1_37_hf1_scorecard_blocks_without_live_gate() -> None:
    scorecard = runner._build_final_scorecard(  # noqa: SLF001
        source_gate={"source_gate": "passed"},
        docs_correction={"docs_state_pre_rerun_correction": "passed"},
        endpoint_matrix={"endpoint_matrix_probe": "passed"},
        timeout_diagnosis={"adaptive_timeout_diagnosis": "passed"},
        latency_profile={"latency_profile_gate": "passed", "recommended_runner_timeout_sec": 60},
        actual_live_smoke={"actual_live_creator_smoke_gate": "blocked", "actual_live_cases_total": 5, "actual_live_cases_passed": 0},
        trace_acceptance={"trace_acceptance_gate": "blocked"},
        rollback_live={"rollback_hard_stop_live_gate": "passed_with_warning"},
        normal_user_live={"normal_user_live_no_effect_gate": "blocked"},
        rag_gate={"rag_behavior_regression_gate": "blocked"},
        provider_budget={"provider_budget_gate": "passed"},
        no_mutation={"no_mutation_proof": "passed"},
        artifact_encoding_hygiene=True,
    )
    assert scorecard["final_status"] == "blocked"
    assert "actual_live_creator_smoke_gate" in scorecard["blockers"]
