# TASKLIST PRD-031: `answer_adaptive.py` Modularization (Wave 17)

## Status Legend
- [ ] pending
- [~] in progress
- [x] done

## Execution Log
- [x] Add fast-path debug bootstrap helper.
- [x] Add fast-path mode directive helper.
- [x] Integrate helper calls into fast-path branch.
- [x] Run targeted tests.
- [x] Run full suite.

## Result Snapshot
- Added in `adaptive_runtime/routing_stage_helpers.py`:
  - `_apply_fast_path_debug_bootstrap(...)`
  - `_build_fast_path_mode_directive(...)`
- Replaced inline fast-path setup block in `answer_adaptive.py`.
- Validation:
  - Targeted: `13 passed`
  - Full suite: `501 passed, 13 skipped`
