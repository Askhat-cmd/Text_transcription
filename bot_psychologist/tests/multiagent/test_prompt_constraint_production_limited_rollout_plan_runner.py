from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_prompt_constraint_production_limited_rollout_plan as runner


def test_rollout_plan_runner_outputs_required_artifacts(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    result = runner.run(
        argparse.Namespace(source_dir="TO_DO_LIST/logs/PRD-046.1.11", output_dir=str(out_dir), strict=True)
    )
    assert result["status"] in {"passed", "blocked", "needs_hotfix"}
    for name in (
        "production_limited_rollout_plan.json",
        "production_limited_cohort_policy.json",
        "production_limited_preflight_gates.json",
        "production_limited_operator_checklist.json",
        "production_limited_monitoring_plan.json",
        "production_limited_rollback_plan.json",
        "production_limited_abort_criteria.json",
        "production_limited_readiness_gate.json",
        "production_limited_operator_runbook.md",
        "no_mutation_proof.json",
        "artifact_encoding_hygiene_report.json",
    ):
        assert (out_dir / name).exists(), name
