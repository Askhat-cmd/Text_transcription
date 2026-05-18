from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_diagnostic_center_runtime_pilot_results_gate as runner


def test_runtime_pilot_results_execution_evidence_review_expected_values(tmp_path: Path) -> None:
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
    payload = json.loads((out_dir / "execution_evidence_review.json").read_text(encoding="utf-8"))
    assert payload["execution_window_count"] == 1
    assert payload["target_user_count"] == 1
    assert payload["allowed_user_ids"] == ["pilot_runtime_operator_001"]
    assert payload["runtime_activation_mode"] == "deterministic_runtime_harness"
    assert payload["provider_called_by_execution_count"] == 0
    assert payload["pilot_apply_count"] == 5
    assert payload["pilot_apply_only_for_allowed_user"] is True
    assert payload["prompt_delta_within_limits"] is True
    assert payload["execution_evidence_status"] == "passed"
