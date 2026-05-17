from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_prompt_constraint_pilot_quality_gate as runner


def test_quality_gate_no_mutation_proof_is_clean(tmp_path: Path) -> None:
    out_dir = tmp_path / "quality_gate"
    runner.run(
        argparse.Namespace(
            input_dir="TO_DO_LIST/logs/PRD-046.1.6",
            output_dir=str(out_dir),
            strict=True,
            allow_missing_runtime_samples="false",
            max_quality_regression_count=0,
            max_rollback_failure_count=0,
            max_safety_violation_count=0,
        )
    )
    proof = json.loads((out_dir / "no_mutation_proof.json").read_text(encoding="utf-8"))
    assert proof["all_blocks_merged_mutated"] is False
    assert proof["registry_mutated"] is False
    assert proof["config_mutated"] is False
    assert proof["chroma_reindex_performed"] is False
    assert proof["production_apply_performed"] is False
    assert proof["provider_called_by_eval_count"] == 0

