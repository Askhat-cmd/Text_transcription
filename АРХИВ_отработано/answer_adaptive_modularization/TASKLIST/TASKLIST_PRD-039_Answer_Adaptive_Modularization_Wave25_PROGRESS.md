# TASKLIST PRD-039: `answer_adaptive.py` Modularization (Wave 25)

## Status Legend
- [ ] pending
- [~] in progress
- [x] done

## Execution Log
- [x] Add helper `_build_prompt_stack_override(...)`.
- [x] Replace duplicated prompt-stack blocks in fast/full generation branches.
- [x] Run targeted tests.
- [x] Run full suite.

## Result Snapshot
- Added in `adaptive_runtime/runtime_misc_helpers.py`:
  - `_build_prompt_stack_override(...)`
- Updated `answer_adaptive.py` to use shared prompt-stack helper in both branches.
- Validation:
  - Targeted: `13 passed`
  - Full suite: `501 passed, 13 skipped`
