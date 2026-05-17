from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_prompt_constraint_supervised_rollout_plan as runner


def test_toggle_matrix_has_required_rows_and_ready_flag(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    runner.run(
        argparse.Namespace(
            input_dir="TO_DO_LIST/logs/PRD-046.1.7",
            output_dir=str(out_dir),
            strict=True,
        )
    )
    payload = json.loads((out_dir / "supervised_rollout_toggle_matrix.json").read_text(encoding="utf-8"))
    assert payload["schema_version"] == "prompt_constraint_supervised_rollout_toggle_matrix_v1"
    assert payload["toggle_matrix_ready"] is True
    assert len(payload["rows"]) >= 10
    assert any(row["force_disabled"] and row["expected"] == "disabled/no_apply" for row in payload["rows"])
