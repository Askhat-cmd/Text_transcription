from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_diagnostic_center_runtime_pilot_results_gate as runner


def test_runtime_pilot_results_encoding_warning_review_is_non_blocking(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    runner.run(
        argparse.Namespace(
            repo_root=".",
            source_dir="TO_DO_LIST/logs/PRD-046.1.20",
            reports_dir="TO_DO_LIST/reports",
            output_dir=str(out_dir),
            strict=True,
        )
    )
    payload = json.loads((out_dir / "encoding_warning_review.json").read_text(encoding="utf-8"))
    assert payload["replacement_char_warning_count"] == 1
    assert payload["encoding_warning_status"] == "non_blocking"
    assert payload["follow_up_required"] is False
