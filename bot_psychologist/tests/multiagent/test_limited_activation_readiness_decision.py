from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_limited_activation_readiness as gate  # noqa: E402


def test_limited_activation_readiness_decision() -> None:
    payload = gate.build_readiness_scorecard(
        source_gate={"source_gate_passed": True},
        live_dependency_gate={"live_dependency_gate_passed": True},
        runtime_boundary_gate={"runtime_boundary_gate_passed": True},
        normal_user_boundary_gate={"normal_user_boundary_gate_passed": True, "normal_user_apply_effect_count": 0, "normal_user_provider_call_count": 0},
        allowlist_policy_gate={"allowlist_policy_gate_passed": True},
        rollback_hard_stop_gate={"rollback_hard_stop_gate_passed": True},
        safety_kb_boundary_gate={"safety_kb_boundary_gate_passed": True, "raw_content_full_exposure_count": 0, "authority_citation_count": 0},
        trace_provider_sanitization_gate={"trace_provider_sanitization_gate_passed": True, "raw_provider_payload_committed": False, "secrets_committed": False},
        runtime_defaults_gate={"runtime_defaults_gate_passed": True, "runtime_defaults_changed": False},
        provider_budget_policy_gate={"provider_budget_policy_gate_passed": True},
        no_mutation_proof={"no_mutation_proof_passed": True, "production_data_mutated": False, "runtime_defaults_changed": False},
        artifact_encoding_hygiene_passed=True,
        docs_consistency_gate={"docs_consistency_gate_passed": True},
    )
    assert payload["final_status"] == "passed"
    assert payload["decision"] == "ready_for_allowlisted_limited_live_activation_prd"

