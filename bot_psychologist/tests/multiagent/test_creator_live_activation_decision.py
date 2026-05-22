from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_creator_live_activation as gate  # noqa: E402


def test_creator_live_activation_decision_passed() -> None:
    scorecard = gate.build_live_activation_scorecard(
        source_gate={"source_gate_passed": True},
        creator_identity_gate={"creator_identity_gate_passed": True},
        admin_runtime_controls_gate={"admin_runtime_controls_gate_passed": True},
        web_chat_smoke={"smoke_passed": True, "creator_path_active": True},
        normal_user_gate={"normal_user_no_effect_gate_passed": True, "normal_user_apply_effect_count": 0},
        active_influence_gate={"active_influence_gate_passed": True},
        rollback_gate={"rollback_kill_switch_gate_passed": True},
        hard_stop_gate={"hard_stop_gate_passed": True, "hard_stop_triggered": False},
        safety_gate={"safety_kb_boundary_gate_passed": True},
        trace_gate={
            "trace_provider_sanitization_gate_passed": True,
            "raw_provider_payload_committed": False,
            "raw_private_logs_committed": False,
        },
        trace_storage_gate={"trace_storage_gate_passed": True},
        monitor_gate={"monitor_gate_passed": True},
        trace_clearance_gate={"trace_clearance_policy_gate_passed": True},
        provider_budget_gate={"provider_budget_gate_passed": True},
        no_mutation_proof={"no_mutation_proof_passed": True, "kb_registry_chroma_config_mutated": False},
        artifact_encoding_hygiene_passed=True,
        docs_consistency_gate={"docs_consistency_gate_passed": True},
    )
    assert scorecard["final_status"] == "passed"
    assert scorecard["decision"] == "creator_live_activation_passed"
