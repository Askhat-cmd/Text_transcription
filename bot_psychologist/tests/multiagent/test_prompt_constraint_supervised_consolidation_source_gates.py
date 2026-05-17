from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_prompt_constraint_supervised_consolidation_gate as runner


def _copy_source_logs(src_a: Path, src_b: Path) -> None:
    src_a_origin = Path("TO_DO_LIST/logs/PRD-046.1.9")
    src_b_origin = Path("TO_DO_LIST/logs/PRD-046.1.10")
    src_a.mkdir(parents=True, exist_ok=True)
    src_b.mkdir(parents=True, exist_ok=True)

    for name in (
        "supervised_execution_observability_scorecard.json",
        "supervised_execution_baseline_vs_test_apply.json",
        "supervised_execution_normal_user_no_effect.json",
        "supervised_execution_rollback_proof.json",
        "no_mutation_proof.json",
        "artifact_encoding_hygiene_report.json",
    ):
        shutil.copy2(src_a_origin / name, src_a / name)

    for name in (
        "supervised_continuation_observability_scorecard.json",
        "supervised_continuation_scenario_coverage.json",
        "supervised_continuation_baseline_vs_test_apply.json",
        "supervised_continuation_normal_user_no_effect.json",
        "supervised_continuation_rollback_proof.json",
        "no_mutation_proof.json",
        "artifact_encoding_hygiene_report.json",
    ):
        shutil.copy2(src_b_origin / name, src_b / name)


def test_runner_blocked_when_source_a_not_passed(tmp_path: Path) -> None:
    src_a = tmp_path / "a"
    src_b = tmp_path / "b"
    _copy_source_logs(src_a, src_b)

    score_a_path = src_a / "supervised_execution_observability_scorecard.json"
    score_a = json.loads(score_a_path.read_text(encoding="utf-8"))
    score_a["final_status"] = "blocked"
    score_a_path.write_text(json.dumps(score_a, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    out_dir = tmp_path / "out"
    result = runner.run(
        argparse.Namespace(source_a_dir=str(src_a), source_b_dir=str(src_b), output_dir=str(out_dir), strict=True)
    )
    assert result["status"] == "blocked"


def test_runner_blocked_when_source_b_decision_not_continue_supervised(tmp_path: Path) -> None:
    src_a = tmp_path / "a"
    src_b = tmp_path / "b"
    _copy_source_logs(src_a, src_b)

    score_b_path = src_b / "supervised_continuation_observability_scorecard.json"
    score_b = json.loads(score_b_path.read_text(encoding="utf-8"))
    score_b["decision"] = "stay_limited"
    score_b_path.write_text(json.dumps(score_b, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    out_dir = tmp_path / "out"
    result = runner.run(
        argparse.Namespace(source_a_dir=str(src_a), source_b_dir=str(src_b), output_dir=str(out_dir), strict=True)
    )
    assert result["status"] == "blocked"
