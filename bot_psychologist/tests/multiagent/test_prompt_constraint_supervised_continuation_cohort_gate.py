from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_prompt_constraint_supervised_continuation_gate as runner


def test_cohort_gate_respected(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    runner.run(argparse.Namespace(source_dir="TO_DO_LIST/logs/PRD-046.1.9", output_dir=str(out_dir), strict=True))
    manifest = json.loads((out_dir / "supervised_continuation_manifest.json").read_text(encoding="utf-8"))
    cohort = manifest["cohort"]
    assert cohort["actual_size"] <= 6
    assert cohort["normal_users_included"] is False
    assert cohort["all_user_ids_allowlisted_or_test_prefix"] is True
