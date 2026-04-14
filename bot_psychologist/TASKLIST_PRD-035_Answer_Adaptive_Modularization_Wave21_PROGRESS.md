# TASKLIST PRD-035: `answer_adaptive.py` Modularization (Wave 21)

## Status Legend
- [ ] pending
- [~] in progress
- [x] done

## Execution Log
- [x] Add helper `_run_validation_retry_generation(...)`.
- [x] Replace duplicated fast/full retry generation callbacks.
- [x] Keep output-validation flow and metadata contract intact.
- [x] Run targeted tests.
- [x] Run full suite.

## Result Snapshot
- Added in `adaptive_runtime/runtime_misc_helpers.py`:
  - `_run_validation_retry_generation(...)`
- Updated `answer_adaptive.py`:
  - fast-path retry callback now uses shared helper
  - full-path retry callback now uses shared helper
- Validation:
  - Targeted: `13 passed`
  - Full suite: `501 passed, 13 skipped`
