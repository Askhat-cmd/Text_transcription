from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_diagnostic_center_stabilization_cleanup as runner


def test_cleanup_plan_non_destructive(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    reports_dir = tmp_path / "reports"
    runner.run(
        argparse.Namespace(source_dir="TO_DO_LIST/logs/PRD-046.1.14", repo_root=".", output_dir=str(out_dir), reports_dir=str(reports_dir), strict=True)
    )
    payload = json.loads((out_dir / "diagnostic_center_cleanup_plan.json").read_text(encoding="utf-8"))
    assert payload["cleanup_mode"] == "non_destructive_manifest_first"
    assert payload["physical_deletion_performed"] is False
    assert payload["runtime_files_deleted"] is False
    assert payload["regression_gates_deleted"] is False
    assert payload["kb_registry_chroma_config_mutated"] is False
