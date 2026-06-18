from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bot_psychologist.eval.prd_047_26_schema import (
    CONTROLLED_CASE_TYPES,
    CONTROLLED_FAILURE_CLASSES,
    default_cases_path,
    load_cases,
    validate_cases,
)
from bot_psychologist.tools.prd_047_26_live_quality_triage import build_dry_run_report


def test_cases_schema_has_minimum_coverage() -> None:
    cases = load_cases(default_cases_path())
    report = validate_cases(cases)
    assert report["status"] == "passed"
    assert report["case_count"] >= 12
    for case_type in {
        "direct_kb_answer",
        "elliptical_followup",
        "summary_request",
        "practice_request",
        "support",
        "overlay_noise_probe",
    }:
        assert report["type_counts"][case_type] >= 1


def test_case_ids_unique_and_failure_candidates_controlled() -> None:
    cases = load_cases(default_cases_path())
    ids = [str(case["case_id"]) for case in cases]
    assert len(ids) == len(set(ids))
    for case in cases:
        assert str(case["case_type"]) in CONTROLLED_CASE_TYPES
        for candidate in case["failure_class_candidates"]:
            assert str(candidate) in CONTROLLED_FAILURE_CLASSES


def test_dry_run_report_is_valid_with_passed_inputs(tmp_path: Path) -> None:
    cases = load_cases(default_cases_path())
    cases_validation = validate_cases(cases)
    source_gate = {"status": "passed", "blockers": [], "warnings": []}
    report = build_dry_run_report(source_gate=source_gate, cases_validation=cases_validation, out_dir=tmp_path)
    assert report["status"] == "passed"
    assert report["case_count"] >= 12
    assert (tmp_path / "dry_run_report.json").exists()
