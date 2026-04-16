# TASKLIST PRD-033: `answer_adaptive.py` Modularization (Wave 19)

## Status Legend
- [ ] pending
- [~] in progress
- [x] done

## Execution Log
- [x] Add helper `_generate_llm_with_trace(...)` in runtime misc module.
- [x] Replace duplicated LLM generate+trace blocks in fast/full branches.
- [x] Keep validation retry flow unchanged.
- [x] Run targeted tests.
- [x] Run full suite.

## Result Snapshot
- Added in `adaptive_runtime/runtime_misc_helpers.py`:
  - `_generate_llm_with_trace(...)`
- Updated `answer_adaptive.py`:
  - fast-path LLM stage now uses shared helper
  - full-path LLM stage now uses shared helper
- Validation:
  - Targeted: `13 passed`
  - Full suite: `501 passed, 13 skipped`
