from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_prompt_constraint_supervised_consolidation_gate as runner


REQUIRED_RISK_IDS = {
    "limited_evidence_size",
    "synthetic_test_only_cohort",
    "runtime_env_drift",
    "prompt_bloat_under_real_long_context",
    "unexpected_diagnostic_center_divergence",
    "rollback_operator_error",
    "trace_artifact_leakage",
    "overfitting_to_eval_fixtures",
}


def test_risk_register_contains_required_risks(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    runner.run(
        argparse.Namespace(
            source_a_dir="TO_DO_LIST/logs/PRD-046.1.9",
            source_b_dir="TO_DO_LIST/logs/PRD-046.1.10",
            output_dir=str(out_dir),
            strict=True,
        )
    )
    payload = json.loads((out_dir / "supervised_consolidation_risk_register.json").read_text(encoding="utf-8"))
    risk_ids = {item["risk_id"] for item in payload["risks"]}
    assert REQUIRED_RISK_IDS.issubset(risk_ids)
    assert payload["risk_register_has_blockers"] is False
    assert payload["blocking_risk_count"] == 0
