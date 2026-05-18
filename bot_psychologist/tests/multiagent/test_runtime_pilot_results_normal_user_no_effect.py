from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_diagnostic_center_runtime_pilot_results_gate as runner


def test_runtime_pilot_results_normal_user_no_effect_review_expected_values(tmp_path: Path) -> None:
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
    payload = json.loads((out_dir / "normal_user_no_effect_review.json").read_text(encoding="utf-8"))
    assert payload["normal_user_control_count"] == 2
    assert payload["normal_user_apply_count"] == 0
    assert payload["writer_prompt_changed_for_normal_user"] is False
    assert payload["writer_contract_changed_for_normal_user"] is False
    assert payload["final_answer_changed_for_normal_user"] is False
    assert payload["normal_user_provider_apply_count"] == 0
    assert payload["normal_user_trace_sanitized"] is True
    assert payload["normal_user_no_effect_status"] == "passed"
