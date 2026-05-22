from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import validate_prd_artifact_encoding as encoding_validator  # noqa: E402


def test_creator_live_activation_artifact_hygiene() -> None:
    report = encoding_validator.run(
        argparse.Namespace(
            prd="PRD-046.1.33",
            logs_dir="TO_DO_LIST/logs/PRD-046.1.33",
            reports_dir="TO_DO_LIST/reports",
            out_dir="TO_DO_LIST/logs/PRD-046.1.33",
            report_prd="PRD-046.1.33",
            repo_root=".",
            fixed_file=[],
        )
    )
    assert report["final_status"] == "passed"
