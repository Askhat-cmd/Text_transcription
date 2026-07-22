# PRD-047.42-APPLY-25 Implementation Report

- PRD: `PRD-047.42-APPLY-25`
- Status: `accepted`
- Delivery: `main_commit=b2c4c48`, `push_status=pushed_to_origin_main`
- Type: hygiene micro-PRD (one assertion, one test file)

## Scope Delivered

- Retired the hard `assert len(rules) == 75` equality check inside `test_rule_count_matches_boundary_map_inventory` in `bot_psychologist/tests/contract/test_prd_047_42_apply_20_enforce_compliance_mapping.py`.
- Added a docstring explaining why the exact count is not a permanent invariant: classifier-style decomposition (APPLY-23/24) legitimately collapses nested `if` cascades into flat dispatch checks, which lowers the live AST count with every such slice (APPLY-24 alone: `75 -> 67`).
- Left the two remaining assertions in the same function untouched (`payload["metadata"]["rule_count"] == len(rules)` self-consistency check, `len(rules) >= 40` sanity floor) - both retain diagnostic value.
- Left the other two test functions in the file (`test_snapshot_build_is_deterministic_and_timestamp_normalized`, `test_runner_writes_expected_reports`) untouched.
- Touched no production code (`writer_agent*.py` untouched) and no `TO_DO_LIST/logs/PRD-047.42-APPLY-20/` artifact.

## Honest Boundary

- This is a hygiene-only micro-PRD, not a content slice. It does not advance the `_enforce_answer_compliance` decomposition; the next content PRD is `mvp_free_branch_handoff` (line ~746), per the v4.28 master plan update.

## Verification Summary

- Focused file run (`test_prd_047_42_apply_20_enforce_compliance_mapping.py`): `3 passed`.
- Full contract suite (`test_prd_047_42_apply_*.py`, owner workspace, dirty tree containing only this PRD's own change): `131 passed, 1 warning` - up from `130 passed, 1 failed` before this PRD, confirming the previously honestly-documented APPLY-24 finding is now fully resolved.
- Clean-tree historical contract rerun (temporary detached worktree from commit `b2c4c48`): `131 passed, 1 warning` - fully green, no exceptions.
- Canonical isolated writer baseline (same worktree): `19 failed, 240 passed, 2024 deselected, 190 warnings` - identical to APPLY-24's recorded numbers; this test was never part of `-k writer` selection, so the count could not and did not move.
- Owner workspace writer baseline: `14 failed, 245 passed, 2024 deselected, 346 warnings` - identical to APPLY-24's recorded numbers, confirming zero side effects outside the one touched assertion.
- `no_mutation_proof.md`: `0` changed protected paths across the `21` canonical protected files; `0` changed paths under `TO_DO_LIST/logs/PRD-047.42-APPLY-20/`; full PRD diff scope is exactly one file.
