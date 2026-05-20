from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_controlled_rollout_results_gate as gate  # noqa: E402


def test_controlled_rollout_results_gate_decision() -> None:
    payload = gate.build_decision_gate(
        source_gate={
            "source_gate_passed": True,
            "missing_source_artifact_count": 0,
            "source_final_status": "passed",
            "source_decision": "controlled_rollout_execution_passed_ready_for_results_gate",
        },
        execution_evidence={
            "new_execution_performed": False,
            "provider_called_by_results_gate": False,
            "target_operator_count": 3,
            "scenario_count": 12,
            "provider_calls_total": 12,
        },
        provider_budget={"provider_budget_gate_passed": True},
        normal_user={
            "normal_user_controls_total": 3,
            "normal_user_apply_count": 0,
            "normal_user_provider_calls_total": 0,
            "normal_user_no_effect_passed": True,
        },
        quality={
            "quality_micro_shift_gate_passed": True,
            "candidate_weaker_than_baseline_count": 0,
            "hard_fail_count": 0,
            "response_quality_regression_count": 0,
        },
        rollback={
            "rollback_gate_passed": True,
            "rollback_failure_count": 0,
            "stale_apply_after_force_disabled_count": 0,
            "hard_stop_triggered": False,
        },
        safety={
            "safety_kb_boundary_gate_passed": True,
            "raw_kb_text_exposure_count": 0,
            "kb_authority_violation_count": 0,
            "unsafe_practice_suggestion_count": 0,
        },
        trace={
            "trace_provider_sanitization_gate_passed": True,
            "raw_provider_payload_committed_count": 0,
            "secret_like_value_count": 0,
            "private_log_leak_count": 0,
        },
        botdb={
            "botdb_stability_gate_passed": True,
            "botdb_query_ok": True,
            "botdb_semantic_fallback_used": False,
        },
        no_mutation={
            "no_mutation_proof_passed": True,
            "runtime_defaults_changed": False,
            "production_data_mutated": False,
            "kb_registry_chroma_config_mutated": False,
        },
        artifact_hygiene={
            "artifact_encoding_hygiene_passed": True,
            "utf8_decode_error_count": 0,
            "nul_byte_file_count": 0,
            "json_parse_error_count": 0,
            "replacement_char_warning_count": 0,
        },
        docs_consistency={
            "docs_consistency_passed": True,
            "project_state_synced": True,
            "roadmap_synced": True,
            "prd_index_synced": True,
            "decisions_synced": True,
            "stale_next_prd_reference_count": 0,
            "duplicate_roadmap_next_item_count": 0,
        },
    )
    assert payload["final_status"] == "passed"
    assert payload["decision"] == "ready_for_limited_runtime_activation_readiness_prd"
