# TASKLIST PRD-050: `answer_adaptive.py` Modularization (Wave 36)

## Status Legend
- [ ] pending
- [~] in progress
- [x] done

## Execution Log
- [x] Add helper `_refresh_context_and_apply_trace_snapshot(...)` in trace helpers.
- [x] Replace duplicated fast-path snapshot/context trace block.
- [x] Replace duplicated full-path snapshot/context trace block.
- [x] Preserve trace contracts: `snapshot_v11`, `snapshot_v12`, `context_mode`.
- [x] Run targeted tests.
- [x] Attempt full suite (`--maxfail=1`).

## Result Snapshot
- Updated `adaptive_runtime/trace_helpers.py`:
  - `_refresh_context_and_apply_trace_snapshot(...)`
- Updated `answer_adaptive.py`:
  - two duplicated runtime snapshot blocks replaced with helper call
- Validation:
  - Targeted: `13 passed`
  - Full suite: `501 passed, 13 skipped`
