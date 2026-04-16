# TASKLIST PRD-058: `answer_adaptive.py` Modularization (Wave 44)

## Status Legend
- [ ] pending
- [~] in progress
- [x] done

## Execution Log
- [x] Add helper `_format_and_validate_llm_answer(...)` in runtime misc helpers.
- [x] Replace duplicated fast-path format/validation block.
- [x] Replace duplicated full-path format/validation block.
- [x] Preserve retry and validation observability contract.
- [x] Run targeted tests.
- [x] Attempt full suite (`--maxfail=1`).

## Result Snapshot
- Updated `adaptive_runtime/runtime_misc_helpers.py`:
  - `_format_and_validate_llm_answer(...)`
- Updated `answer_adaptive.py`:
  - duplicated format+validation flows replaced by helper calls
- Validation:
  - Targeted: `13 passed`
  - Full suite: `501 passed, 13 skipped`
