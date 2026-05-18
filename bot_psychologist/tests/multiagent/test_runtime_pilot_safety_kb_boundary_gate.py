from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_diagnostic_center_runtime_pilot_execution as runner


def test_runtime_pilot_safety_kb_boundary_gate_passes(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    runner.run(
        argparse.Namespace(
            repo_root=".",
            source_dir="TO_DO_LIST/logs/PRD-046.1.19",
            output_dir=str(out_dir),
            reports_dir="TO_DO_LIST/reports",
            strict=True,
        )
    )
    payload = json.loads((out_dir / "safety_kb_boundary_gate.json").read_text(encoding="utf-8"))
    assert payload["safety_kb_boundary_gate_passed"] is True
    assert payload["raw_kb_quote_exposure_count"] == 0
    assert payload["kuznitsa_authority_citation_count"] == 0

