from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_diagnostic_center_runtime_pilot_results_gate as runner


def test_runtime_pilot_results_safety_kb_boundary_review_expected_values(tmp_path: Path) -> None:
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
    payload = json.loads((out_dir / "safety_kb_boundary_review.json").read_text(encoding="utf-8"))
    assert payload["safety_kb_boundary_gate_passed"] is True
    assert payload["raw_kb_quote_exposure_count"] == 0
    assert payload["kuznitsa_authority_citation_count"] == 0
    assert payload["internal_only_direct_use_count"] == 0
    assert payload["not_for_direct_quote_violation_count"] == 0
    assert payload["high_stakes_directive_advice_count"] == 0
    assert payload["safety_regression_count"] == 0
    assert payload["kb_boundary_violation_count"] == 0
    assert payload["chunk_type_authority"] == "deterministic"
    assert payload["allowed_use_authority"] == "deterministic"
    assert payload["safety_flags_authority"] == "deterministic"
    assert payload["llm_enrichment_role"] == "advisory"
    assert payload["kuznitsa_duha_role"] == "internal_lens_library"
    assert payload["safety_kb_boundary_status"] == "passed"
