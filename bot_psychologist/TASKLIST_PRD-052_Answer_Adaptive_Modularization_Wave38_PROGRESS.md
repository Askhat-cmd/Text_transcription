# TASKLIST PRD-052: `answer_adaptive.py` Modularization (Wave 38)

## Status Legend
- [ ] pending
- [~] in progress
- [x] done

## Execution Log
- [x] Add helper `_apply_output_validation_observability(...)` in trace helpers.
- [x] Replace duplicated fast-path post-validation block.
- [x] Replace duplicated full-path post-validation block.
- [x] Preserve branch behavior: retry LLM call trace recorded only in full-path.
- [x] Run targeted tests.
- [x] Attempt full suite (`--maxfail=1`).

## Result Snapshot
- Updated `adaptive_runtime/trace_helpers.py`:
  - `_apply_output_validation_observability(...)`
- Updated `answer_adaptive.py`:
  - duplicated post-validation observability blocks replaced by helper
- Validation:
  - Targeted: `13 passed`
  - Full suite: `501 passed, 13 skipped`
