from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_prompt_constraint_pilot_quality_gate as runner


def test_quality_delta_detects_weaker_candidate_constraints(tmp_path: Path) -> None:
    src = Path("TO_DO_LIST/logs/PRD-046.1.6")
    input_dir = tmp_path / "input_046_1_6"
    shutil.copytree(src, input_dir)

    eval_path = input_dir / "prompt_constraint_pilot_runtime_eval.json"
    payload = json.loads(eval_path.read_text(encoding="utf-8"))
    cases = payload["cases"]
    target = next(
        item
        for item in cases
        if item.get("decision", {}).get("activation_mode") == "test_apply"
        and item.get("decision", {}).get("apply_to_writer_prompt") is True
    )
    target["decision"]["candidate_constraints"]["depth_limit"] = "high"
    target["decision"]["candidate_constraints"]["max_questions"] = 3
    eval_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    out_dir = tmp_path / "out_046_1_7"
    runner.run(
        argparse.Namespace(
            input_dir=str(input_dir),
            output_dir=str(out_dir),
            strict=False,
            allow_missing_runtime_samples="false",
            max_quality_regression_count=0,
            max_rollback_failure_count=0,
            max_safety_violation_count=0,
        )
    )
    delta = json.loads((out_dir / "baseline_vs_test_apply_quality_delta.json").read_text(encoding="utf-8"))
    assert delta["candidate_weaker_than_baseline_count"] > 0
    assert delta["quality_delta_decision"] in {"needs_hf", "blocked"}

