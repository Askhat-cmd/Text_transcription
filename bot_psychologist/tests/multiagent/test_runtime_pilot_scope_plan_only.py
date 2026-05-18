from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_diagnostic_center_runtime_pilot_readiness as runner


def test_runtime_pilot_scope_is_plan_only(tmp_path: Path) -> None:
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
    scope = json.loads((out_dir / "pilot_scope.json").read_text(encoding="utf-8"))
    assert scope["pilot_type"] == "limited_live_smoke_plan_only"
    assert scope["execution_performed"] is False
    assert scope["provider_called"] is False
