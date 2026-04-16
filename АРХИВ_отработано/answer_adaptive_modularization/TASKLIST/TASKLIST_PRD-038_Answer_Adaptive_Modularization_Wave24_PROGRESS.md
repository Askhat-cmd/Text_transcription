# TASKLIST PRD-038: `answer_adaptive.py` Modularization (Wave 24)

## Status Legend
- [ ] pending
- [~] in progress
- [x] done

## Execution Log
- [x] Add helper `_collect_llm_session_metrics(...)`.
- [x] Replace duplicated token/session metric blocks in fast/full success branches.
- [x] Run targeted tests.
- [x] Run full suite.

## Result Snapshot
- Added in `adaptive_runtime/runtime_misc_helpers.py`:
  - `_collect_llm_session_metrics(...)`
- Updated `answer_adaptive.py` to use shared metrics helper in both branches.
- Validation:
  - Targeted: `13 passed`
  - Full suite: `501 passed, 13 skipped`
