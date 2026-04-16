# TASKLIST PRD-149: `answer_adaptive.py` Modularization (Wave 135)

## Status Legend
- [ ] pending
- [~] in progress
- [x] done

## Execution Log
- [x] Create `retrieval_pipeline_helpers.py` and move reusable retrieval pipeline helpers.
- [x] Reduce `retrieval_stage_helpers.py` to orchestration function `_run_retrieval_routing_context_stage`.
- [x] Run targeted tests for runtime generation/validation/trace contracts.
- [x] Run full suite with local TMP/TEMP override.

## Result Snapshot
- `retrieval_stage_helpers.py`: `581 -> 252` lines.
- New module `retrieval_pipeline_helpers.py`: `336` lines.
- Validation:
  - Targeted: `15 passed`
  - Full suite: `501 passed, 13 skipped`
