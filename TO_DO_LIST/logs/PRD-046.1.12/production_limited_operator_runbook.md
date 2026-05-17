# PRD-046.1.12 Production-Limited Operator Runbook

This runbook is plan-only. Do not execute rollout in PRD-046.1.12.

## Steps
1. `confirm_scope` - Confirm this is production-limited execution, not broad rollout.
2. `confirm_allowlist` - Confirm only explicitly allowlisted user IDs are included.
3. `confirm_force_disabled_start` - Confirm FORCE_DISABLED starts as true before any run.
4. `capture_baseline_no_mutation` - Capture hashes before execution.
5. `enable_for_limited_window_only` - Enable test_apply only for limited manual window.
6. `capture_trace_samples` - Capture sanitized trace samples.
7. `run_normal_user_control` - Verify normal user path remains unchanged.
8. `rollback_force_disabled` - Set FORCE_DISABLED=true and verify no stale apply.
9. `compare_quality` - Compare baseline vs production-limited test_apply.
10. `final_decision` - Choose continue_limited/stay_limited/hotfix/stop after gate.

## Hard Rules
- Keep `PROMPT_CONSTRAINT_PILOT_ENABLED=false` as baseline default.
- Keep `PROMPT_CONSTRAINT_PILOT_FORCE_DISABLED=true` as baseline default.
- No provider calls for planning stage.
- No mutation of KB/registry/config/chroma.
- Use sanitized traces only.
