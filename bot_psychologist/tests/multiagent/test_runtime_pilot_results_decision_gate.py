from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_diagnostic_center_runtime_pilot_results_gate as runner


def test_runtime_pilot_results_decision_gate_expected_values(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    result = runner.run(
        argparse.Namespace(
            repo_root=".",
            source_dir="TO_DO_LIST/logs/PRD-046.1.20",
            reports_dir="TO_DO_LIST/reports",
            output_dir=str(out_dir),
            strict=True,
        )
    )
    payload = json.loads((out_dir / "runtime_pilot_results_decision_gate.json").read_text(encoding="utf-8"))
    scorecard = json.loads((out_dir / "runtime_pilot_results_scorecard.json").read_text(encoding="utf-8"))
    assert payload["final_status"] == "passed"
    assert payload["decision"] == "continue_limited_candidate"
    assert payload["source_gate_passed"] is True
    assert payload["execution_evidence_status"] == "passed"
    assert payload["rollback_evidence_status"] == "passed"
    assert payload["normal_user_no_effect_status"] == "passed"
    assert payload["quality_gate_decision"] == "passed"
    assert payload["safety_kb_boundary_status"] == "passed"
    assert payload["trace_sanitization_status"] == "passed"
    assert payload["artifact_hygiene_status"] == "passed"
    assert payload["encoding_warning_status"] == "non_blocking"
    assert payload["no_mutation_status"] == "passed"
    assert payload["hard_stop_triggered"] is False
    assert payload["broad_rollout_allowed"] is False
    assert payload["production_ready"] is False
    assert "PRD-046.1.22" in payload["recommended_next_prd"]
    assert scorecard["decision"] == "continue_limited_candidate"
    assert result["status"] == "passed"
