from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_prompt_constraint_production_limited_rollout_plan as runner


def test_no_execution_and_no_mutation(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    runner.run(argparse.Namespace(source_dir="TO_DO_LIST/logs/PRD-046.1.11", output_dir=str(out_dir), strict=True))

    readiness = json.loads((out_dir / "production_limited_readiness_gate.json").read_text(encoding="utf-8"))
    assert readiness["execution_performed"] is False
    assert readiness["provider_called_by_plan"] is False
    assert readiness["default_flags_changed"] is False

    proof = json.loads((out_dir / "no_mutation_proof.json").read_text(encoding="utf-8"))
    assert proof["all_blocks_merged_mutated"] is False
    assert proof["registry_mutated"] is False
    assert proof["config_mutated"] is False
    assert proof["chroma_reindex_performed"] is False
    assert proof["production_apply_performed"] is False
    assert proof["provider_called_by_plan"] is False
    assert proof["execution_performed"] is False
