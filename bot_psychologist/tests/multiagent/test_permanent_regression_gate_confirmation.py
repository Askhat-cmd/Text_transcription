from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_final_acceptance as module


def test_permanent_regression_gate_confirmation_has_all_required_classes() -> None:
    source_catalog = {
        "permanent_gates": [
            {"gate_id": "prompt_constraint_default_off_no_effect"},
            {"gate_id": "prompt_constraint_normal_user_no_effect"},
            {"gate_id": "prompt_constraint_force_disabled_rollback"},
            {"gate_id": "prompt_constraint_safety_regression"},
            {"gate_id": "prompt_constraint_kb_policy_regression"},
            {"gate_id": "prompt_constraint_raw_kb_exposure"},
            {"gate_id": "prompt_constraint_prompt_bloat"},
            {"gate_id": "prompt_constraint_conflict"},
            {"gate_id": "production_no_mutation"},
            {"gate_id": "artifact_encoding_hygiene"},
        ]
    }
    payload = module.confirm_permanent_regression_gates(
        source_gate={"source_gate_passed": True, "provider_called": False},
        source_catalog=source_catalog,
        source_no_mutation={"all_blocks_merged_mutated": False, "registry_mutated": False, "config_mutated": False, "provider_called": False},
        source_hygiene={"final_status": "passed"},
        prompt_baseline_gate={"final_status": "passed"},
        kb_gate={"final_status": "passed"},
        trace_gate={"final_status": "passed"},
        docs_sync={"final_status": "passed"},
    )
    assert len(payload["required_gate_classes"]) == 14
    assert payload["final_status"] == "passed"
