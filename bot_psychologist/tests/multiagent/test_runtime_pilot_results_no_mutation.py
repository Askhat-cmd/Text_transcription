from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_diagnostic_center_runtime_pilot_results_gate as runner


def test_runtime_pilot_results_no_mutation_review_expected_values(tmp_path: Path) -> None:
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
    review = json.loads((out_dir / "no_mutation_review.json").read_text(encoding="utf-8"))
    proof = json.loads((out_dir / "no_mutation_proof.json").read_text(encoding="utf-8"))
    assert review["production_mutation_detected"] is False
    assert review["all_blocks_merged_mutated"] is False
    assert review["registry_mutated"] is False
    assert review["config_mutated"] is False
    assert review["chroma_reindex_performed"] is False
    assert review["runtime_defaults_changed"] is False
    assert review["no_mutation_status"] == "passed"
    assert proof["all_blocks_merged_mutated"] is False
    assert proof["registry_mutated"] is False
    assert proof["config_mutated"] is False
    assert proof["new_execution_performed"] is False
