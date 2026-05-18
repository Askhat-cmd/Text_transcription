from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_diagnostic_center_stabilization_cleanup as runner


def test_stabilization_no_mutation_proof(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    reports_dir = tmp_path / "reports"
    runner.run(
        argparse.Namespace(source_dir="TO_DO_LIST/logs/PRD-046.1.14", repo_root=".", output_dir=str(out_dir), reports_dir=str(reports_dir), strict=True)
    )

    no_mutation = json.loads((out_dir / "no_mutation_proof.json").read_text(encoding="utf-8"))
    scorecard = json.loads((out_dir / "diagnostic_center_stabilization_scorecard.json").read_text(encoding="utf-8"))

    assert no_mutation["all_blocks_merged_mutated"] is False
    assert no_mutation["registry_mutated"] is False
    assert no_mutation["config_mutated"] is False
    assert no_mutation["chroma_reindex_performed"] is False
    assert no_mutation["new_execution_performed"] is False
    assert no_mutation["provider_called"] is False

    assert scorecard["new_execution_performed"] is False
    assert scorecard["provider_called"] is False
    assert scorecard["runtime_defaults_changed"] is False
    assert scorecard["kb_registry_chroma_config_mutated"] is False
    assert scorecard["runtime_files_deleted"] is False
    assert scorecard["regression_gates_deleted"] is False
    assert scorecard["physical_files_deleted"] == 0
