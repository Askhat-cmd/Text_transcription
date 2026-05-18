from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_diagnostic_center_stabilization_cleanup as runner


REQUIRED_GATE_IDS = {
    "prompt_constraint_default_off_no_effect",
    "prompt_constraint_force_disabled_rollback",
    "prompt_constraint_allowlist_enforcement",
    "prompt_constraint_normal_user_no_effect",
    "prompt_constraint_safety_regression",
    "prompt_constraint_kb_policy_regression",
    "prompt_constraint_raw_kb_exposure",
    "prompt_constraint_internal_only_exposure",
    "prompt_constraint_not_for_direct_quote",
    "prompt_constraint_prompt_bloat",
    "prompt_constraint_conflict",
    "prompt_constraint_trace_sanitization",
    "artifact_encoding_hygiene",
    "production_no_mutation",
}


def test_regression_gate_catalog_contains_required_gates(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    reports_dir = tmp_path / "reports"
    runner.run(
        argparse.Namespace(source_dir="TO_DO_LIST/logs/PRD-046.1.14", repo_root=".", output_dir=str(out_dir), reports_dir=str(reports_dir), strict=True)
    )
    payload = json.loads((out_dir / "diagnostic_center_regression_gate_catalog.json").read_text(encoding="utf-8"))
    gate_ids = {item["gate_id"] for item in payload["permanent_gates"]}
    assert REQUIRED_GATE_IDS.issubset(gate_ids)
    assert payload["all_required_gates_present"] is True
    assert len(payload["permanent_gates"]) >= payload["minimum_required_gate_count"]
