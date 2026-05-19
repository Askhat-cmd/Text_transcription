from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_diagnostic_center_controlled_rollout_planning as runner


def test_controlled_rollout_planning_artifact_hygiene(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    result = runner.run(
        argparse.Namespace(
            repo_root=".",
            reports_dir="TO_DO_LIST/reports",
            docs_dir="docs",
            logs_dir="TO_DO_LIST/logs",
            output_dir=str(out_dir),
            strict=False,
        )
    )
    assert result["status"] in {"passed", "blocked", "warning"}
    assert (out_dir / "artifact_hygiene_report.json").exists()
