from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_prompt_constraint_supervised_rollout_plan as runner


def test_supervised_rollout_runner_outputs_required_artifacts(tmp_path: Path) -> None:
    out_dir = tmp_path / "prd_046_1_8"
    result = runner.run(
        argparse.Namespace(
            input_dir="TO_DO_LIST/logs/PRD-046.1.7",
            output_dir=str(out_dir),
            strict=True,
        )
    )
    assert result["status"] in {"passed", "blocked", "needs_hotfix"}
    for name in (
        "supervised_rollout_plan.json",
        "supervised_rollout_readiness_gate.json",
        "supervised_rollout_abort_criteria.json",
        "supervised_rollout_toggle_matrix.json",
        "supervised_rollout_operator_runbook.json",
        "supervised_rollout_operator_runbook.md",
        "no_mutation_proof.json",
        "artifact_encoding_hygiene_report.json",
    ):
        assert (out_dir / name).exists(), name
