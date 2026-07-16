from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from TO_DO_LIST.tools import run_prd_047_42_apply_16_call_llm_slice9 as runner


def test_runner_normalizes_snapshot_timestamp() -> None:
    payload = runner.build_normalized_snapshot()

    assert payload["schema_version"] == "prd_047_42_apply_6_call_llm_snapshot_v1"
    assert payload["generated_at_utc"] == runner.NORMALIZED_TIMESTAMP
    assert [case["case"] for case in payload["cases"]] == [
        "safe_guided_direct",
        "mvp_free_overview",
        "mvp_free_rich_request",
    ]
    assert all("last_debug" in case for case in payload["cases"])
    assert all(
        isinstance(case["last_debug"].get("user_prompt"), str)
        for case in payload["cases"]
    )


def test_compare_snapshot_payloads_reports_user_prompt_identity() -> None:
    before_payload = {
        "cases": [
            {"case": "a", "last_debug": {"user_prompt": "one\nline"}},
            {"case": "b", "last_debug": {"user_prompt": "same"}},
        ]
    }
    after_payload = {
        "cases": [
            {"case": "a", "last_debug": {"user_prompt": "one\nline"}},
            {"case": "b", "last_debug": {"user_prompt": "different"}},
        ]
    }

    comparison = runner.compare_snapshot_payloads(before_payload, after_payload)

    assert comparison["snapshot_byte_identical"] is False
    assert comparison["all_user_prompts_match"] is False
    by_case = {case["case"]: case for case in comparison["cases"]}
    assert by_case["a"]["user_prompt_match"] is True
    assert by_case["b"]["user_prompt_match"] is False
    assert "line 1" in by_case["b"]["first_diff"]


def test_runner_writes_expected_reports(tmp_path: Path) -> None:
    reports = runner.write_reports(tmp_path)

    expected_names = {
        "call_llm_snapshot_after.json",
        "no_mutation_proof.md",
        "extraction_log.md",
        "implementation_report.md",
        "next_recommendation.md",
    }
    assert {path.name for path in reports.values()} == expected_names
    assert all(path.exists() for path in reports.values())

    snapshot = json.loads(
        (tmp_path / "call_llm_snapshot_after.json").read_text(encoding="utf-8")
    )
    assert snapshot["generated_at_utc"] == runner.NORMALIZED_TIMESTAMP
    assert all("user_prompt" in case["last_debug"] for case in snapshot["cases"])

    no_mutation = (tmp_path / "no_mutation_proof.md").read_text(encoding="utf-8")
    assert "Protected diff result: `0 changed paths`" in no_mutation
