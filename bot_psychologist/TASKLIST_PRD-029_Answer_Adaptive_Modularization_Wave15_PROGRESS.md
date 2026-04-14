# TASKLIST PRD-029: `answer_adaptive.py` Modularization (Wave 15)

## Status Legend
- [ ] pending
- [~] in progress
- [x] done

## Execution Log
- [x] Add progressive feedback helper.
- [x] Add voyage rerank debug payload helper.
- [x] Add routing debug payload helper.
- [x] Replace inline Stage 3 blocks with helper calls.
- [x] Run targeted tests.
- [x] Run full suite.

## Result Snapshot
- Added in `adaptive_runtime/trace_helpers.py`:
  - `_collect_progressive_feedback_blocks(...)`
  - `_build_voyage_rerank_debug_payload(...)`
  - `_build_routing_debug_payload(...)`
- Simplified Stage 3 debug/rerank sections in `answer_adaptive.py`.
- Validation:
  - Targeted: `13 passed`
  - Full suite: `501 passed, 13 skipped`
