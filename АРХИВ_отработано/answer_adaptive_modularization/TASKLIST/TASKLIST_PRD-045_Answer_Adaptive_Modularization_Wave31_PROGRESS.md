# TASKLIST PRD-045: `answer_adaptive.py` Modularization (Wave 31)

## Status Legend
- [ ] pending
- [~] in progress
- [x] done

## Execution Log
- [x] Add helper `_attach_routing_stage_debug_trace(...)` in routing-stage helpers.
- [x] Replace inline routing debug-trace population block in Stage 3 full-path flow.
- [x] Preserve routing/trace key contract for Web UI.
- [x] Run targeted tests.
- [x] Attempt full suite (environment-limited).

## Result Snapshot
- Updated `adaptive_runtime/routing_stage_helpers.py`:
  - `_attach_routing_stage_debug_trace(...)`
- Updated `answer_adaptive.py`:
  - inline routing-stage trace payload assignment replaced with helper call
- Validation:
  - Targeted: `13 passed`
  - Full suite: attempted, blocked by host pytest temp-directory ACL issue
    (`PermissionError` under `%TEMP%\\pytest-of-Reklama-3D`).
