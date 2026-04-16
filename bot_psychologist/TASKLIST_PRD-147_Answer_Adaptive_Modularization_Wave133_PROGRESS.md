# TASKLIST PRD-147: `answer_adaptive.py` Modularization (Wave 133)

## Status Legend
- [ ] pending
- [~] in progress
- [x] done

## Execution Log
- [x] Create `routing_pre_stage_helpers.py` and move pre-routing pipeline helpers.
- [x] Create `routing_context_helpers.py` and move routing context/practice/debug helpers.
- [x] Rewrite `routing_stage_helpers.py` as compatibility re-export façade.
- [x] Run targeted tests for runtime generation/validation/trace contracts.
- [x] Run full suite with local TMP/TEMP override.

## Result Snapshot
- `routing_stage_helpers.py`: `677 -> 20` lines (compatibility façade).
- New modules:
  - `routing_pre_stage_helpers.py`: `295` lines
  - `routing_context_helpers.py`: `385` lines
- Validation:
  - Targeted: `15 passed`
  - Full suite: `501 passed, 13 skipped`
