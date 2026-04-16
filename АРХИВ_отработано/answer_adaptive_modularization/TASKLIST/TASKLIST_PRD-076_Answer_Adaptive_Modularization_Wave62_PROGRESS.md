# TASKLIST PRD-076: `answer_adaptive.py` Modularization (Wave 62)

## Status Legend
- [ ] pending
- [~] in progress
- [x] done

## Execution Log
- [x] Add `_prepare_hybrid_query_stage(...)` in retrieval helpers.
- [x] Replace inline hybrid-query preparation block in `answer_adaptive.py`.
- [x] Run expanded targeted tests.
- [x] Run full suite (`--maxfail=1`).

## Result Snapshot
- Updated `adaptive_runtime/retrieval_stage_helpers.py`:
  - `_prepare_hybrid_query_stage(...)`
- Updated `answer_adaptive.py`:
  - Stage-3 pre-retrieval setup now delegated to helper
- Validation:
  - Expanded targeted: `31 passed`
  - Full suite: `501 passed, 13 skipped`
