from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_prompt_constraint_production_limited_execution_gate as runner


def test_no_mutation_proof_green(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    runner.run(argparse.Namespace(plan_dir="TO_DO_LIST/logs/PRD-046.1.12", output_dir=str(out_dir), strict=True, operator_user_id=None))
    payload = json.loads((out_dir / "no_mutation_proof.json").read_text(encoding="utf-8"))
    assert payload["all_blocks_merged_mutated"] is False
    assert payload["registry_mutated"] is False
    assert payload["config_mutated"] is False
    assert payload["chroma_reindex_performed"] is False
    assert payload["production_apply_performed"] is False
    assert payload["provider_called_by_execution"] is False
