from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_diagnostic_center_runtime_pilot_results_gate as runner


def _copy_source(dst: Path) -> None:
    src = Path("TO_DO_LIST/logs/PRD-046.1.20")
    dst.mkdir(parents=True, exist_ok=True)
    for name in (
        "source_gate.json",
        "preflight_gate.json",
        "execution_manifest.json",
        "toggle_state_before.json",
        "rollback_precheck.json",
        "pilot_operator_trace_samples_sanitized.json",
        "normal_user_control_trace_samples_sanitized.json",
        "limited_live_smoke_results.json",
        "baseline_vs_pilot_quality_delta.json",
        "safety_kb_boundary_gate.json",
        "trace_sanitization_gate.json",
        "rollback_postcheck.json",
        "hard_stop_evaluation.json",
        "monitoring_scorecard.json",
        "no_mutation_proof.json",
        "artifact_encoding_hygiene_report.json",
    ):
        shutil.copy2(src / name, dst / name)


def test_runtime_pilot_results_source_gate_passes(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    result = runner.run(
        argparse.Namespace(
            repo_root=".",
            source_dir="TO_DO_LIST/logs/PRD-046.1.20",
            reports_dir="TO_DO_LIST/reports",
            output_dir=str(out_dir),
            strict=True,
        )
    )
    gate = json.loads((out_dir / "source_gate.json").read_text(encoding="utf-8"))
    assert gate["source_gate_passed"] is True
    assert result["status"] == "passed"


def test_runtime_pilot_results_source_gate_fails_for_wrong_decision(tmp_path: Path) -> None:
    source = tmp_path / "src"
    _copy_source(source)
    score_path = source / "monitoring_scorecard.json"
    payload = json.loads(score_path.read_text(encoding="utf-8"))
    payload["decision"] = "blocked_runtime_pilot_execution"
    score_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out_dir = tmp_path / "out"
    result = runner.run(
        argparse.Namespace(
            repo_root=".",
            source_dir=str(source),
            reports_dir="TO_DO_LIST/reports",
            output_dir=str(out_dir),
            strict=True,
        )
    )
    gate = json.loads((out_dir / "source_gate.json").read_text(encoding="utf-8"))
    assert gate["source_gate_passed"] is False
    assert result["status"] != "passed"
