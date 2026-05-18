from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_diagnostic_center_stabilization_cleanup as runner


def _copy_source(dst: Path) -> None:
    src = Path("TO_DO_LIST/logs/PRD-046.1.14")
    dst.mkdir(parents=True, exist_ok=True)
    for name in (
        "production_limited_results_manifest.json",
        "production_limited_quality_summary.json",
        "production_limited_rollback_summary.json",
        "production_limited_normal_user_summary.json",
        "production_limited_trace_sanitization_summary.json",
        "production_limited_post_run_risk_register.json",
        "production_limited_results_decision_gate.json",
        "no_mutation_proof.json",
        "artifact_encoding_hygiene_report.json",
    ):
        shutil.copy2(src / name, dst / name)


def test_runner_blocked_when_source_not_passed(tmp_path: Path) -> None:
    source = tmp_path / "src"
    _copy_source(source)
    gate = source / "production_limited_results_decision_gate.json"
    payload = json.loads(gate.read_text(encoding="utf-8"))
    payload["final_status"] = "blocked"
    gate.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result = runner.run(
        argparse.Namespace(source_dir=str(source), repo_root=".", output_dir=str(tmp_path / "out"), reports_dir=str(tmp_path / "reports"), strict=True)
    )
    assert result["status"] == "blocked"


def test_runner_blocked_when_source_decision_wrong(tmp_path: Path) -> None:
    source = tmp_path / "src"
    _copy_source(source)
    gate = source / "production_limited_results_decision_gate.json"
    payload = json.loads(gate.read_text(encoding="utf-8"))
    payload["decision"] = "stay_limited"
    gate.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result = runner.run(
        argparse.Namespace(source_dir=str(source), repo_root=".", output_dir=str(tmp_path / "out"), reports_dir=str(tmp_path / "reports"), strict=True)
    )
    assert result["status"] == "blocked"
