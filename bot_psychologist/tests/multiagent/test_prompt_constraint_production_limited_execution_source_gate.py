from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_prompt_constraint_production_limited_execution_gate as runner


def _copy_plan(dst: Path) -> None:
    src = Path("TO_DO_LIST/logs/PRD-046.1.12")
    dst.mkdir(parents=True, exist_ok=True)
    for name in (
        "production_limited_rollout_plan.json",
        "production_limited_cohort_policy.json",
        "production_limited_preflight_gates.json",
        "production_limited_operator_checklist.json",
        "production_limited_monitoring_plan.json",
        "production_limited_rollback_plan.json",
        "production_limited_abort_criteria.json",
        "production_limited_readiness_gate.json",
        "no_mutation_proof.json",
        "artifact_encoding_hygiene_report.json",
    ):
        shutil.copy2(src / name, dst / name)


def test_runner_blocked_when_source_plan_not_passed(tmp_path: Path) -> None:
    plan = tmp_path / "plan"
    _copy_plan(plan)
    path = plan / "production_limited_readiness_gate.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["final_status"] = "blocked"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result = runner.run(argparse.Namespace(plan_dir=str(plan), output_dir=str(tmp_path / "out"), strict=True, operator_user_id=None))
    assert result["status"] == "blocked"


def test_runner_blocked_when_source_plan_decision_wrong(tmp_path: Path) -> None:
    plan = tmp_path / "plan"
    _copy_plan(plan)
    path = plan / "production_limited_readiness_gate.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["decision"] = "stay_supervised"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result = runner.run(argparse.Namespace(plan_dir=str(plan), output_dir=str(tmp_path / "out"), strict=True, operator_user_id=None))
    assert result["status"] == "blocked"
