from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_diagnostic_center_stabilization_cleanup as runner


REQUIRED_CATEGORIES = {
    "production_runtime",
    "runtime_contracts",
    "regression_gates",
    "eval_harness",
    "prd_artifacts",
    "archive_candidates",
    "docs_living_state",
    "do_not_touch",
}


def test_module_classification_has_required_categories(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    reports_dir = tmp_path / "reports"
    runner.run(
        argparse.Namespace(source_dir="TO_DO_LIST/logs/PRD-046.1.14", repo_root=".", output_dir=str(out_dir), reports_dir=str(reports_dir), strict=True)
    )
    payload = json.loads((out_dir / "diagnostic_center_module_classification.json").read_text(encoding="utf-8"))
    counts = payload["category_counts"]
    assert REQUIRED_CATEGORIES.issubset(set(counts.keys()))
    assert payload["required_categories_present"] is True
