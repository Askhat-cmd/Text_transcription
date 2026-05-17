from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_prompt_constraint_pilot_quality_gate as runner


def test_quality_gate_runner_outputs_required_artifacts(tmp_path: Path) -> None:
    out_dir = tmp_path / "prd_046_1_7"
    result = runner.run(
        argparse.Namespace(
            input_dir="TO_DO_LIST/logs/PRD-046.1.6",
            output_dir=str(out_dir),
            strict=True,
            allow_missing_runtime_samples="false",
            max_quality_regression_count=0,
            max_rollback_failure_count=0,
            max_safety_violation_count=0,
        )
    )
    assert result["status"] in {"passed", "passed_with_limited_evidence", "needs_hf", "blocked"}
    for name in (
        "runtime_evidence_audit.json",
        "rollback_toggle_matrix.json",
        "baseline_vs_test_apply_quality_delta.json",
        "prompt_constraint_pilot_gate_verification.json",
        "prompt_constraint_pilot_quality_gate_scorecard.json",
        "no_mutation_proof.json",
        "artifact_encoding_hygiene_report.json",
    ):
        assert (out_dir / name).exists()


def test_missing_source_artifacts_returns_explicit_blocked_status(tmp_path: Path) -> None:
    missing_input = tmp_path / "missing"
    missing_input.mkdir(parents=True, exist_ok=True)
    out_dir = tmp_path / "out"
    result = runner.run(
        argparse.Namespace(
            input_dir=str(missing_input),
            output_dir=str(out_dir),
            strict=True,
            allow_missing_runtime_samples="false",
            max_quality_regression_count=0,
            max_rollback_failure_count=0,
            max_safety_violation_count=0,
        )
    )
    scorecard = json.loads((out_dir / "prompt_constraint_pilot_quality_gate_scorecard.json").read_text(encoding="utf-8"))
    assert result["status"] == "blocked_missing_prd_046_1_6_artifacts"
    assert scorecard["final_status"] == "blocked_missing_prd_046_1_6_artifacts"
