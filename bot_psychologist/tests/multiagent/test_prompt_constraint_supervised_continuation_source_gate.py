from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_prompt_constraint_supervised_continuation_gate as runner


def _copy_source_logs(dst: Path) -> None:
    src = Path("TO_DO_LIST/logs/PRD-046.1.9")
    dst.mkdir(parents=True, exist_ok=True)
    for name in (
        "supervised_execution_manifest.json",
        "supervised_execution_trace_samples.json",
        "supervised_execution_baseline_vs_test_apply.json",
        "supervised_execution_normal_user_no_effect.json",
        "supervised_execution_rollback_proof.json",
        "supervised_execution_observability_scorecard.json",
        "no_mutation_proof.json",
        "artifact_encoding_hygiene_report.json",
    ):
        shutil.copy2(src / name, dst / name)


def test_runner_blocked_when_source_status_not_passed(tmp_path: Path) -> None:
    src = tmp_path / "src"
    _copy_source_logs(src)
    path = src / "supervised_execution_observability_scorecard.json"
    score = json.loads(path.read_text(encoding="utf-8"))
    score["final_status"] = "blocked"
    path.write_text(json.dumps(score, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out_dir = tmp_path / "out"
    result = runner.run(argparse.Namespace(source_dir=str(src), output_dir=str(out_dir), strict=True))
    assert result["status"] == "blocked"


def test_runner_blocked_when_source_decision_not_continue_supervised(tmp_path: Path) -> None:
    src = tmp_path / "src"
    _copy_source_logs(src)
    path = src / "supervised_execution_observability_scorecard.json"
    score = json.loads(path.read_text(encoding="utf-8"))
    score["decision"] = "stay_limited"
    path.write_text(json.dumps(score, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out_dir = tmp_path / "out"
    result = runner.run(argparse.Namespace(source_dir=str(src), output_dir=str(out_dir), strict=True))
    assert result["status"] == "blocked"
