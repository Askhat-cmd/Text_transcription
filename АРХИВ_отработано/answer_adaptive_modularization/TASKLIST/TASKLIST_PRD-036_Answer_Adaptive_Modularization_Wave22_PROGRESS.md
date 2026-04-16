# TASKLIST PRD-036: `answer_adaptive.py` Modularization (Wave 22)

## Status Legend
- [ ] pending
- [~] in progress
- [x] done

## Execution Log
- [x] Add helper `_finalize_failure_debug_trace(...)` in trace helpers.
- [x] Replace duplicated failure trace finalization in partial path.
- [x] Replace duplicated failure trace finalization in LLM error path.
- [x] Replace duplicated failure trace finalization in outer exception path.
- [x] Run targeted tests.
- [x] Run full suite.

## Result Snapshot
- Added in `adaptive_runtime/trace_helpers.py`:
  - `_finalize_failure_debug_trace(...)`
- Updated `answer_adaptive.py` failure branches to use shared helper.
- Validation:
  - Targeted: `13 passed`
  - Full suite: `501 passed, 13 skipped`
