from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_prompt_constraint_production_limited_results_gate as runner


def _copy_source(dst: Path) -> None:
    src = Path("TO_DO_LIST/logs/PRD-046.1.13")
    dst.mkdir(parents=True, exist_ok=True)
    for name in (
        "production_limited_execution_manifest.json",
        "production_limited_preflight_result.json",
        "production_limited_trace_samples.json",
        "production_limited_baseline_vs_test_apply.json",
        "production_limited_normal_user_no_effect.json",
        "production_limited_rollback_proof.json",
        "production_limited_monitoring_scorecard.json",
        "no_mutation_proof.json",
        "artifact_encoding_hygiene_report.json",
    ):
        shutil.copy2(src / name, dst / name)


def test_runner_blocked_when_source_execution_not_passed(tmp_path: Path) -> None:
    source = tmp_path / "src"
    _copy_source(source)
    path = source / "production_limited_monitoring_scorecard.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["final_status"] = "blocked"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result = runner.run(argparse.Namespace(source_dir=str(source), output_dir=str(tmp_path / "out"), strict=True))
    assert result["status"] == "blocked"


def test_runner_blocked_when_source_decision_wrong(tmp_path: Path) -> None:
    source = tmp_path / "src"
    _copy_source(source)
    path = source / "production_limited_monitoring_scorecard.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["decision"] = "stay_limited"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result = runner.run(argparse.Namespace(source_dir=str(source), output_dir=str(tmp_path / "out"), strict=True))
    assert result["status"] == "blocked"
