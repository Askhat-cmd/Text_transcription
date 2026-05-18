from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_diagnostic_center_runtime_pilot_readiness as runner


def test_rollback_first_runbook_has_mandatory_entries(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    runner.run(
        argparse.Namespace(
            repo_root=".",
            source_dir="TO_DO_LIST/logs/PRD-046.1.18",
            output_dir=str(out_dir),
            reports_dir="TO_DO_LIST/reports",
            strict=True,
        )
    )
    payload = json.loads((out_dir / "rollback_first_runbook.json").read_text(encoding="utf-8"))
    assert payload["rollback_must_be_tested_before_pilot_apply"] is True
    assert payload["rollback_must_be_tested_after_pilot_apply"] is True
    assert payload["stale_apply_after_force_disabled_is_blocker"] is True
