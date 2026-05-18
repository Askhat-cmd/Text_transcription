from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_diagnostic_center_final_acceptance as runner


def test_final_acceptance_no_mutation_proof(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    reports_dir = tmp_path / "reports"
    runner.run(
        argparse.Namespace(
            source_dir="TO_DO_LIST/logs/PRD-046.1.15",
            repo_root=".",
            output_dir=str(out_dir),
            reports_dir=str(reports_dir),
            strict=True,
        )
    )

    no_mutation = json.loads((out_dir / "no_mutation_proof.json").read_text(encoding="utf-8"))
    scorecard = json.loads((out_dir / "diagnostic_center_v1_final_acceptance_scorecard.json").read_text(encoding="utf-8"))

    assert no_mutation["all_blocks_merged_mutated"] is False
    assert no_mutation["registry_mutated"] is False
    assert no_mutation["config_mutated"] is False
    assert no_mutation["chroma_reindex_performed"] is False
    assert no_mutation["new_execution_performed"] is False
    assert no_mutation["provider_called"] is False

    assert scorecard["new_execution_performed"] is False
    assert scorecard["provider_called"] is False
    assert scorecard["production_mutation_detected"] is False
