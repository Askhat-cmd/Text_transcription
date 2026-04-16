# TASKLIST PRD-027: `answer_adaptive.py` Modularization (Wave 13)

## Status Legend
- [ ] pending
- [~] in progress
- [x] done

## Execution Log
- [x] Add success debug payload helper.
- [x] Add success debug-trace finalization helper.
- [x] Integrate helpers in fast-path success branch.
- [x] Integrate helpers in full success branch.
- [x] Run targeted tests.
- [x] Run full suite.

## Result Snapshot
- Added:
  - `_attach_debug_payload(...)` in `adaptive_runtime/response_utils.py (removed in Wave 142)`
  - `_finalize_success_debug_trace(...)` in `adaptive_runtime/trace_helpers.py`
- Replaced duplicated success debug handling in `answer_adaptive.py`.
- Validation:
  - Targeted: `13 passed`
  - Full suite: `501 passed, 13 skipped`

