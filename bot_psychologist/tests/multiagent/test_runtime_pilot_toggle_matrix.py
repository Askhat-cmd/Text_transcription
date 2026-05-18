from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_diagnostic_center_runtime_pilot_readiness as runner


def test_runtime_pilot_toggle_matrix_defaults(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    runner.run(
        argparse.Namespace(
            repo_root=".",
            source_dir="TO_DO_LIST/logs/PRD-046.1.18",
            output_dir=str(out_dir),
            reports_dir="TO_DO_LIST/reports",
            strict=True,
        )
    )
    matrix = json.loads((out_dir / "toggle_matrix.json").read_text(encoding="utf-8"))
    values = matrix["matrix"]
    assert values["PROMPT_CONSTRAINT_PILOT_ENABLED"]["default_state"] == "false"
    assert values["PROMPT_CONSTRAINT_PILOT_FORCE_DISABLED"]["default_state"] == "true"
