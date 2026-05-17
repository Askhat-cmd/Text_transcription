# PRD-046.1.8 Supervised Rollout Operator Runbook

- PRD: `PRD-046.1.8`
- Stage: `plan_only_no_execution`

## Steps
1. Run preflight and verify PRD-046.1.7 final_status=passed and decision=supervised_rollout_candidate.
2. Keep defaults conservative: enabled=false and force_disabled=true before any supervised request.
3. For supervised execution PRD, manually set flags only for the approved session cohort.
4. Keep initial cohort size <= 3 and allowlisted/test-prefix only.
5. Capture trace artifacts after each supervised run and verify normal_user_apply_count=0.
6. Verify rollback matrix by toggling force_disabled=true and confirming no stale apply.
7. Disable pilot immediately by setting force_disabled=true and enabled=false if any abort condition is hit.
8. Store rollout artifacts: scorecard, gate verification, quality delta, no-mutation proof, encoding report.
9. Compare baseline vs test_apply metrics for every supervised cycle before continuation.
10. Block next supervised step automatically if any hard abort condition is triggered.

## Rollback / Off Steps
1. Set PROMPT_CONSTRAINT_PILOT_FORCE_DISABLED=true immediately.
2. Set PROMPT_CONSTRAINT_PILOT_ENABLED=false immediately.
3. Keep PROMPT_CONSTRAINT_PILOT_MODE=shadow for inspection-only traces.
4. Collect trace artifacts and verify normal_user_apply_count=0.
5. Re-run supervised rollout gates before any re-enable request.
