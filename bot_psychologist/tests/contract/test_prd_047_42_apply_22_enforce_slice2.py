from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from TO_DO_LIST.tools import run_prd_047_42_apply_22_enforce_slice2 as runner


def test_before_after_snapshots_are_byte_identical_and_timestamp_normalized() -> None:
    before_payload = runner.build_before_snapshot()
    after_payload = runner.build_after_snapshot()
    comparison = runner.compare_snapshots(before_payload, after_payload)

    assert before_payload == after_payload
    assert before_payload["generated_at_utc"] == runner.NORMALIZED_TIMESTAMP
    assert after_payload["generated_at_utc"] == runner.NORMALIZED_TIMESTAMP
    assert before_payload["metadata"]["case_count"] == 17
    assert comparison["snapshot_byte_identical"] is True
    assert comparison["all_last_debug_keys_match"] is True


def test_close_gently_case_hits_true_branch_and_others_hit_false_branch() -> None:
    after_payload = runner.build_after_snapshot()
    cases_by_name = {case["case"]: case for case in after_payload["cases"]}

    close_gently_case = cases_by_name["close_gently_obligation"]
    close_gently_keys = close_gently_case["last_debug_keys"]
    assert "final_answer_shape" in close_gently_keys
    assert close_gently_keys.index("final_answer_shape") == 15
    assert "answer_fit_evaluator" not in close_gently_keys

    non_early_return_case = cases_by_name["bounded_practice_be_strong"]
    assert "answer_fit_evaluator" in non_early_return_case["last_debug_keys"]


def test_runner_writes_expected_reports_and_grep_proof(tmp_path: Path) -> None:
    reports = runner.write_reports(tmp_path)

    expected_names = {
        "enforce_slice2_snapshot_before.json",
        "enforce_slice2_snapshot_after.json",
        "snapshot_equivalence.md",
        "no_mutation_proof.md",
        "implementation_report.md",
        "next_recommendation.md",
        "grep_proof.md",
    }
    assert {path.name for path in reports.values()} == expected_names
    assert all(path.exists() for path in reports.values())

    before_snapshot = json.loads((tmp_path / "enforce_slice2_snapshot_before.json").read_text(encoding="utf-8"))
    after_snapshot = json.loads((tmp_path / "enforce_slice2_snapshot_after.json").read_text(encoding="utf-8"))
    assert before_snapshot == after_snapshot
    assert before_snapshot["generated_at_utc"] == runner.NORMALIZED_TIMESTAMP

    grep_proof = (tmp_path / "grep_proof.md").read_text(encoding="utf-8")
    assert "Historical slice2 window uses assignment-only pattern: `True`" in grep_proof
    for symbol in runner.REMOVED_IMPORT_SYMBOLS:
        assert f"| `{symbol}` | `[]` |" in grep_proof

    no_mutation = (tmp_path / "no_mutation_proof.md").read_text(encoding="utf-8")
    assert "Protected diff result: `0 changed paths`" in no_mutation
    assert "APPLY-20/APPLY-21 logs diff result: `0 changed paths`" in no_mutation
