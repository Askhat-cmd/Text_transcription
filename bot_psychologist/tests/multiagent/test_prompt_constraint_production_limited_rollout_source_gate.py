from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_prompt_constraint_production_limited_rollout_plan as runner


def _copy_source_logs(dst: Path) -> None:
    src = Path("TO_DO_LIST/logs/PRD-046.1.11")
    dst.mkdir(parents=True, exist_ok=True)
    for name in (
        "supervised_consolidation_manifest.json",
        "supervised_consolidation_aggregate_metrics.json",
        "supervised_consolidation_reproducibility.json",
        "supervised_consolidation_risk_register.json",
        "supervised_consolidation_rollout_decision_gate.json",
        "no_mutation_proof.json",
        "artifact_encoding_hygiene_report.json",
    ):
        shutil.copy2(src / name, dst / name)


def test_runner_blocked_when_source_not_passed(tmp_path: Path) -> None:
    src = tmp_path / "src"
    _copy_source_logs(src)
    path = src / "supervised_consolidation_rollout_decision_gate.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["final_status"] = "blocked"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result = runner.run(argparse.Namespace(source_dir=str(src), output_dir=str(tmp_path / "out"), strict=True))
    assert result["status"] == "blocked"


def test_runner_blocked_when_source_decision_not_prepare_plan(tmp_path: Path) -> None:
    src = tmp_path / "src"
    _copy_source_logs(src)
    path = src / "supervised_consolidation_rollout_decision_gate.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["decision"] = "stay_supervised"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result = runner.run(argparse.Namespace(source_dir=str(src), output_dir=str(tmp_path / "out"), strict=True))
    assert result["status"] == "blocked"
