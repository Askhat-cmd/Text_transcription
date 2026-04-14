# TASKLIST PRD-071: `answer_adaptive.py` Modularization (Wave 57)

## Status Legend
- [ ] pending
- [~] in progress
- [x] done

## Execution Log
- [x] Add `_run_state_and_pre_routing_pipeline(...)` in routing helpers.
- [x] Replace inline stage-2/pre-routing orchestration in `answer_adaptive.py`.
- [x] Route fast-path branch through already extracted `_run_fast_path_stage(...)` helper path.
- [x] Remove dead wrappers/import aliases superseded by new flow.
- [x] Run targeted tests.
- [x] Run full suite (`--maxfail=1`).

## Result Snapshot
- Updated `adaptive_runtime/routing_stage_helpers.py`:
  - `_run_state_and_pre_routing_pipeline(...)`
- Updated `answer_adaptive.py`:
  - stage-2/pre-routing branch now uses high-level helper
  - fast-path branch wired through extracted helper path
  - dead wrapper/import cleanup
- Validation:
  - Targeted: `22 passed`
  - Full suite: `501 passed, 13 skipped`
