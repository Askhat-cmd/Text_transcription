from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_diagnostic_center_stabilization_cleanup as runner


def test_archive_manifest_non_destructive(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    reports_dir = tmp_path / "reports"
    runner.run(
        argparse.Namespace(source_dir="TO_DO_LIST/logs/PRD-046.1.14", repo_root=".", output_dir=str(out_dir), reports_dir=str(reports_dir), strict=True)
    )
    payload = json.loads((out_dir / "diagnostic_center_archive_manifest.json").read_text(encoding="utf-8"))
    assert payload["archive_mode"] in {"manifest_only", "non_destructive_move"}
    assert payload["physical_files_deleted"] == 0
    assert all(item["delete_now"] is False for item in payload["items"])
