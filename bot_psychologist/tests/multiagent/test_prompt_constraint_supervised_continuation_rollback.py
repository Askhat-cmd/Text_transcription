from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_prompt_constraint_supervised_continuation_gate as runner


def test_rollback_gate_has_zero_failures(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    runner.run(argparse.Namespace(source_dir="TO_DO_LIST/logs/PRD-046.1.9", output_dir=str(out_dir), strict=True))
    payload = json.loads((out_dir / "supervised_continuation_rollback_proof.json").read_text(encoding="utf-8"))
    assert payload["rollback_cases_total"] == 6
    assert payload["rollback_cases_passed"] == 6
    assert payload["rollback_failure_count"] == 0
    assert payload["stale_apply_after_force_disabled_count"] == 0
    assert payload["force_disabled_absolute_priority"] is True
