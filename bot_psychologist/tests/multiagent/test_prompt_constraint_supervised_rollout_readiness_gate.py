from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_prompt_constraint_supervised_rollout_plan as runner


def _copy_source_logs(dst: Path) -> None:
    src = Path("TO_DO_LIST/logs/PRD-046.1.7")
    dst.mkdir(parents=True, exist_ok=True)
    for name in (
        "runtime_evidence_audit.json",
        "rollback_toggle_matrix.json",
        "baseline_vs_test_apply_quality_delta.json",
        "prompt_constraint_pilot_gate_verification.json",
        "prompt_constraint_pilot_quality_gate_scorecard.json",
        "no_mutation_proof.json",
        "artifact_encoding_hygiene_report.json",
    ):
        shutil.copy2(src / name, dst / name)


def test_readiness_gate_passes_for_current_source() -> None:
    out_dir = Path("TO_DO_LIST/logs/PRD-046.1.8/_tmp_test_readiness_pass")
    result = runner.run(
        argparse.Namespace(
            input_dir="TO_DO_LIST/logs/PRD-046.1.7",
            output_dir=str(out_dir),
            strict=True,
        )
    )
    gate = json.loads((out_dir / "supervised_rollout_readiness_gate.json").read_text(encoding="utf-8"))
    assert result["status"] == "passed"
    assert gate["final_status"] == "passed"
    assert gate["decision"] == "ready_for_supervised_execution_prd"


def test_readiness_gate_blocked_when_source_decision_not_candidate(tmp_path: Path) -> None:
    src = tmp_path / "input"
    _copy_source_logs(src)
    scorecard_path = src / "prompt_constraint_pilot_quality_gate_scorecard.json"
    scorecard = json.loads(scorecard_path.read_text(encoding="utf-8"))
    scorecard["decision"] = "stay_limited"
    scorecard_path.write_text(json.dumps(scorecard, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    out_dir = tmp_path / "out"
    result = runner.run(
        argparse.Namespace(
            input_dir=str(src),
            output_dir=str(out_dir),
            strict=True,
        )
    )
    gate = json.loads((out_dir / "supervised_rollout_readiness_gate.json").read_text(encoding="utf-8"))
    assert result["status"] == "blocked"
    assert gate["final_status"] == "blocked"
    assert "source_prd_046_1_7_decision_not_supervised_rollout_candidate" in gate["blockers"]
