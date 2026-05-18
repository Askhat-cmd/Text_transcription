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


def test_trace_sanitization_summary_detects_raw_prompt(tmp_path: Path) -> None:
    source = tmp_path / "src"
    _copy_source(source)
    trace_path = source / "production_limited_trace_samples.json"
    trace_payload = json.loads(trace_path.read_text(encoding="utf-8"))
    trace_payload["samples"][0]["raw_prompt_saved"] = True
    trace_path.write_text(json.dumps(trace_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    out_dir = tmp_path / "out"
    result = runner.run(argparse.Namespace(source_dir=str(source), output_dir=str(out_dir), strict=True))

    summary = json.loads((out_dir / "production_limited_trace_sanitization_summary.json").read_text(encoding="utf-8"))
    gate = json.loads((out_dir / "production_limited_results_decision_gate.json").read_text(encoding="utf-8"))
    assert summary["raw_prompt_saved_count"] == 1
    assert summary["trace_sanitization_failed"] is True
    assert summary["trace_sanitization_gate_passed"] is False
    assert gate["decision"] == "stop"
    assert result["status"] == "blocked"
