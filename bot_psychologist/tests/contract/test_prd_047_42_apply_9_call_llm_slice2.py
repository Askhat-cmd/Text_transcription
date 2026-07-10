from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from TO_DO_LIST.tools import run_prd_047_42_apply_9_call_llm_slice2 as runner


def test_runner_normalizes_snapshot_timestamp() -> None:
    payload = runner.build_normalized_snapshot()

    assert payload["schema_version"] == "prd_047_42_apply_6_call_llm_snapshot_v1"
    assert payload["generated_at_utc"] == runner.NORMALIZED_TIMESTAMP
    assert [case["case"] for case in payload["cases"]] == [
        "safe_guided_direct",
        "mvp_free_overview",
        "mvp_free_rich_request",
    ]


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

    snapshot = json.loads((tmp_path / "call_llm_snapshot_after.json").read_text(encoding="utf-8"))
    assert snapshot["generated_at_utc"] == runner.NORMALIZED_TIMESTAMP

    no_mutation = (tmp_path / "no_mutation_proof.md").read_text(encoding="utf-8")
    assert "Protected diff result: `0 changed paths`" in no_mutation
