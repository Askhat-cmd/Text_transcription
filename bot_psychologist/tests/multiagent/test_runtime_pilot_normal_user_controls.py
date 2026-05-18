from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_diagnostic_center_runtime_pilot_execution as runner


def test_runtime_pilot_normal_user_controls(tmp_path: Path) -> None:
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
    results = json.loads((out_dir / "limited_live_smoke_results.json").read_text(encoding="utf-8"))
    assert results["normal_user_apply_count"] == 0
    assert results["writer_prompt_changed_for_normal_user"] is False
    assert results["writer_contract_changed_for_normal_user"] is False
    assert results["final_answer_changed_for_normal_user"] is False

