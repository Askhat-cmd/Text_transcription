from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from TO_DO_LIST.tools import run_prd_047_42_apply_20_enforce_compliance_mapping as runner


def test_snapshot_build_is_deterministic_and_timestamp_normalized() -> None:
    first = runner.build_normalized_snapshot()
    second = runner.build_normalized_snapshot()

    assert first == second
    assert first["generated_at_utc"] == runner.NORMALIZED_TIMESTAMP
    assert first["metadata"]["case_count"] >= 12
    assert first["metadata"]["uncovered_rule_count"] > 0


def test_rule_count_matches_boundary_map_inventory() -> None:
    """Live AST rule count vs. the APPLY-20 boundary map inventory.

    The exact count (75 at APPLY-20 authorship time) is NOT a permanent
    invariant: classifier-style decomposition (introduced in APPLY-23,
    applied at scale in APPLY-24) legitimately collapses nested `if`
    cascades into flat dispatch checks, which lowers this live AST
    count with every such slice. APPLY-24 alone dropped it from 75 to
    67 -- 10 collapsed conditionals replaced by 2 dispatch checks in
    writer_agent.py, a fully expected and behavior-preserving change,
    independently verified byte-identical via snapshot comparison.
    This test therefore checks only internal self-consistency (snapshot
    metadata matches the live inventory) and a loose sanity floor, not
    equality with the original 75. Full analysis: docs/MASTER_
    STRATEGIC_PLAN_NEO_MindBot_v4_RU.md v4.28 and
    TO_DO_LIST/logs/PRD-047.42-APPLY-24/implementation_report.md.
    """
    payload = runner.build_normalized_snapshot()
    rules = runner.build_rule_inventory()

    assert payload["metadata"]["rule_count"] == len(rules)
    assert len(rules) >= 40


def test_runner_writes_expected_reports(tmp_path: Path) -> None:
    reports = runner.write_reports(tmp_path)

    expected_names = {
        "enforce_compliance_boundary_map.md",
        "enforce_compliance_snapshot.json",
        "rule_coverage_log.md",
        "no_mutation_proof.md",
        "implementation_report.md",
        "next_recommendation.md",
    }
    assert {path.name for path in reports.values()} == expected_names
    assert all(path.exists() for path in reports.values())

    snapshot = json.loads((tmp_path / "enforce_compliance_snapshot.json").read_text(encoding="utf-8"))
    assert snapshot["generated_at_utc"] == runner.NORMALIZED_TIMESTAMP
    assert snapshot["metadata"]["rule_count"] == len(runner.build_rule_inventory())

    no_mutation = (tmp_path / "no_mutation_proof.md").read_text(encoding="utf-8")
    assert "Protected diff result: `0 changed paths`" in no_mutation

    coverage = (tmp_path / "rule_coverage_log.md").read_text(encoding="utf-8")
    assert "## НЕПОКРЫТЫЕ ПРАВИЛА" in coverage
