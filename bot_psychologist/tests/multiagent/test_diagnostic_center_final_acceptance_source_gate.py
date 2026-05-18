from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_diagnostic_center_final_acceptance as runner


def _copy_source(dst: Path) -> None:
    src = Path("TO_DO_LIST/logs/PRD-046.1.15")
    dst.mkdir(parents=True, exist_ok=True)
    for name in (
        "diagnostic_center_stabilization_scorecard.json",
        "diagnostic_center_regression_gate_catalog.json",
        "no_mutation_proof.json",
        "artifact_encoding_hygiene_report.json",
    ):
        shutil.copy2(src / name, dst / name)


def test_runner_failed_when_source_not_passed(tmp_path: Path) -> None:
    source = tmp_path / "src"
    _copy_source(source)
    scorecard_path = source / "diagnostic_center_stabilization_scorecard.json"
    scorecard = json.loads(scorecard_path.read_text(encoding="utf-8"))
    scorecard["final_status"] = "blocked"
    scorecard_path.write_text(json.dumps(scorecard, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result = runner.run(
        argparse.Namespace(
            source_dir=str(source),
            repo_root=".",
            output_dir=str(tmp_path / "out"),
            reports_dir=str(tmp_path / "reports"),
            strict=True,
        )
    )
    assert result["status"] == "failed"
