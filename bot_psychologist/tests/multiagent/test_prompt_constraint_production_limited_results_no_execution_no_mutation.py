from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_prompt_constraint_production_limited_results_gate as runner


def test_no_execution_and_no_mutation_proof(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    runner.run(argparse.Namespace(source_dir="TO_DO_LIST/logs/PRD-046.1.13", output_dir=str(out_dir), strict=True))

    manifest = json.loads((out_dir / "production_limited_results_manifest.json").read_text(encoding="utf-8"))
    no_mutation = json.loads((out_dir / "no_mutation_proof.json").read_text(encoding="utf-8"))

    assert manifest["new_execution_performed"] is False
    assert no_mutation["new_execution_performed"] is False
    assert no_mutation["all_blocks_merged_mutated"] is False
    assert no_mutation["registry_mutated"] is False
    assert no_mutation["config_mutated"] is False
    assert no_mutation["chroma_reindex_performed"] is False
    assert no_mutation["production_apply_performed"] is False
    assert no_mutation["provider_called_by_results_gate"] is False
