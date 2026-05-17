from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_prompt_constraint_supervised_rollout_plan as runner


def test_plan_keeps_default_flags_conservative(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    runner.run(
        argparse.Namespace(
            input_dir="TO_DO_LIST/logs/PRD-046.1.7",
            output_dir=str(out_dir),
            strict=True,
        )
    )
    plan = json.loads((out_dir / "supervised_rollout_plan.json").read_text(encoding="utf-8"))
    defaults = plan["baseline_defaults"]
    assert defaults["PROMPT_CONSTRAINT_PILOT_ENABLED"] is False
    assert defaults["PROMPT_CONSTRAINT_PILOT_FORCE_DISABLED"] is True
    assert defaults["PROMPT_CONSTRAINT_PILOT_MODE"] == "shadow|test_apply"
