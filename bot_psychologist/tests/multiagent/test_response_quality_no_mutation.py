from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_diagnostic_center_response_quality_eval as runner


def test_response_quality_no_mutation_proof(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    runner.run(
        argparse.Namespace(
            repo_root=".",
            source_dir="TO_DO_LIST/logs/PRD-046.1.16",
            scenarios="bot_psychologist/tests/fixtures/diagnostic_center_response_quality_scenarios.json",
            rubric="bot_psychologist/tests/fixtures/diagnostic_center_response_quality_rubric.json",
            response_candidates="bot_psychologist/tests/fixtures/diagnostic_center_response_quality_response_candidates.json",
            output_dir=str(out_dir),
            reports_dir=str(tmp_path / "reports"),
            strict=True,
        )
    )
    no_mutation = json.loads((out_dir / "no_mutation_proof.json").read_text(encoding="utf-8"))
    assert no_mutation["all_blocks_merged_mutated"] is False
    assert no_mutation["registry_mutated"] is False
    assert no_mutation["config_mutated"] is False
    assert no_mutation["chroma_reindex_performed"] is False
    assert no_mutation["provider_called"] is False
