from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_diagnostic_center_runtime_pilot_execution as runner


def test_runtime_pilot_execution_toggle_and_rollback(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    runner.run(
        argparse.Namespace(
            repo_root=".",
            source_dir="TO_DO_LIST/logs/PRD-046.1.19",
            output_dir=str(out_dir),
            reports_dir="TO_DO_LIST/reports",
            strict=True,
        )
    )
    toggle = json.loads((out_dir / "toggle_state_before.json").read_text(encoding="utf-8"))
    pre = json.loads((out_dir / "rollback_precheck.json").read_text(encoding="utf-8"))
    post = json.loads((out_dir / "rollback_postcheck.json").read_text(encoding="utf-8"))
    assert toggle["PROMPT_CONSTRAINT_PILOT_FORCE_DISABLED"] is True
    assert pre["rollback_precheck_passed"] is True
    assert post["rollback_postcheck_passed"] is True
    assert post["stale_apply_after_force_disabled_count"] == 0

