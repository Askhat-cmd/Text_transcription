# TASKLIST PRD-037: `answer_adaptive.py` Modularization (Wave 23)

## Status Legend
- [ ] pending
- [~] in progress
- [x] done

## Execution Log
- [x] Add helper `_set_working_state_best_effort(...)` in state helpers.
- [x] Add delegating wrapper in `answer_adaptive.py`.
- [x] Replace duplicated working-state update blocks in fast/partial/success flows.
- [x] Run targeted tests.
- [x] Run full suite.

## Result Snapshot
- Added in `adaptive_runtime/state_helpers.py`:
  - `_set_working_state_best_effort(...)`
- Updated `answer_adaptive.py` to use shared helper in all relevant branches.
- Validation:
  - Targeted: `13 passed`
  - Full suite: `501 passed, 13 skipped`
