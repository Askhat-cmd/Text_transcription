# TASKLIST PRD-056: `answer_adaptive.py` Modularization (Wave 42)

## Status Legend
- [ ] pending
- [~] in progress
- [x] done

## Execution Log
- [x] Add helper `_build_full_path_success_response(...)` in response helpers.
- [x] Replace inline full-path success finalization block with helper call.
- [x] Preserve full-path success/debug-trace contracts.
- [x] Run targeted tests.
- [x] Attempt full suite (`--maxfail=1`).

## Result Snapshot
- Updated `adaptive_runtime/response_utils.py`:
  - `_build_full_path_success_response(...)`
- Updated `answer_adaptive.py`:
  - large full-path success finalization block replaced by helper call
- Validation:
  - Targeted: `13 passed`
  - Full suite: `501 passed, 13 skipped`
