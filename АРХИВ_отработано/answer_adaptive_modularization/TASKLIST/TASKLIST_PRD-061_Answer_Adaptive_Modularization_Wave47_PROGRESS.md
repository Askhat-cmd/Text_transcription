# TASKLIST PRD-061: `answer_adaptive.py` Modularization (Wave 47)

## Status Legend
- [ ] pending
- [~] in progress
- [x] done

## Execution Log
- [x] Add helper `_run_retrieval_and_rerank_stage(...)` in retrieval runtime helpers.
- [x] Replace inline stage-3 retrieval/rerank orchestration in `answer_adaptive.py` with helper call.
- [x] Preserve variable contract for downstream routing/cap/full-path logic.
- [x] Run targeted tests.
- [x] Run full suite (`--maxfail=1`).

## Result Snapshot
- Updated `adaptive_runtime/retrieval_stage_helpers.py`:
  - `_run_retrieval_and_rerank_stage(...)`
- Updated `answer_adaptive.py`:
  - retrieval/rerank stage replaced with helper call
  - runtime import/wrapper alignment
- Validation:
  - Targeted: `10 passed`
  - Full suite: `501 passed, 13 skipped`
