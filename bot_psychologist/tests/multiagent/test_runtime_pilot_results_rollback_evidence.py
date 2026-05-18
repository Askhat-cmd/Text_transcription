from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_diagnostic_center_runtime_pilot_results_gate as runner


def test_runtime_pilot_results_rollback_evidence_review_expected_values(tmp_path: Path) -> None:
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
    payload = json.loads((out_dir / "rollback_evidence_review.json").read_text(encoding="utf-8"))
    assert payload["rollback_precheck_passed"] is True
    assert payload["rollback_postcheck_passed"] is True
    assert payload["stale_apply_after_force_disabled_count"] == 0
    assert payload["normal_user_apply_after_rollback_count"] == 0
    assert payload["force_disabled_priority_preserved"] is True
    assert payload["rollback_state_restores"]["PROMPT_CONSTRAINT_PILOT_FORCE_DISABLED"] is True
    assert payload["rollback_state_restores"]["PROMPT_CONSTRAINT_PILOT_ENABLED"] is False
    assert payload["rollback_state_restores"]["PROMPT_CONSTRAINT_PILOT_MODE"] == "shadow"
    assert payload["rollback_state_restores"]["PROMPT_CONSTRAINT_PILOT_ALLOWED_USER_IDS"] == ""
    assert payload["rollback_evidence_status"] == "passed"
