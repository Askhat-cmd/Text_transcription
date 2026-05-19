from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_diagnostic_center_provider_backed_smoke_readiness as runner


def test_provider_backed_smoke_no_mutation_proof_expected_values(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    runner.run(
        argparse.Namespace(
            repo_root=".",
            reports_dir="TO_DO_LIST/reports",
            logs_root="TO_DO_LIST/logs",
            output_dir=str(out_dir),
            admin_base_url="http://127.0.0.1:8003",
            strict=True,
        )
    )
    proof = json.loads((out_dir / "no_mutation_proof.json").read_text(encoding="utf-8"))
    assert proof["all_blocks_merged_mutated"] is False
    assert proof["registry_mutated"] is False
    assert proof["config_mutated"] is False
    assert proof["chroma_reindex_performed"] is False
    assert proof["provider_called"] is False
