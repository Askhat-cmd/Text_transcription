from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_prompt_constraint_supervised_execution_gate as runner


def _copy_plan_logs(dst: Path) -> None:
    src = Path("TO_DO_LIST/logs/PRD-046.1.8")
    dst.mkdir(parents=True, exist_ok=True)
    for name in (
        "supervised_rollout_plan.json",
        "supervised_rollout_readiness_gate.json",
        "supervised_rollout_abort_criteria.json",
        "supervised_rollout_toggle_matrix.json",
        "supervised_rollout_operator_runbook.json",
        "no_mutation_proof.json",
        "artifact_encoding_hygiene_report.json",
    ):
        shutil.copy2(src / name, dst / name)


def test_runner_blocked_when_source_plan_not_passed(tmp_path: Path) -> None:
    src = tmp_path / "plan"
    _copy_plan_logs(src)
    gate_path = src / "supervised_rollout_readiness_gate.json"
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    gate["final_status"] = "blocked"
    gate_path.write_text(json.dumps(gate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out_dir = tmp_path / "out"
    result = runner.run(
        argparse.Namespace(
            plan_dir=str(src),
            output_dir=str(out_dir),
            strict=True,
        )
    )
    scorecard = json.loads((out_dir / "supervised_execution_observability_scorecard.json").read_text(encoding="utf-8"))
    assert result["status"] == "blocked"
    assert scorecard["final_status"] == "blocked"


def test_runner_blocked_when_source_plan_decision_not_ready(tmp_path: Path) -> None:
    src = tmp_path / "plan"
    _copy_plan_logs(src)
    gate_path = src / "supervised_rollout_readiness_gate.json"
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    gate["decision"] = "execution_blocked"
    gate_path.write_text(json.dumps(gate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out_dir = tmp_path / "out"
    result = runner.run(
        argparse.Namespace(
            plan_dir=str(src),
            output_dir=str(out_dir),
            strict=True,
        )
    )
    scorecard = json.loads((out_dir / "supervised_execution_observability_scorecard.json").read_text(encoding="utf-8"))
    assert result["status"] == "blocked"
    assert scorecard["final_status"] == "blocked"
