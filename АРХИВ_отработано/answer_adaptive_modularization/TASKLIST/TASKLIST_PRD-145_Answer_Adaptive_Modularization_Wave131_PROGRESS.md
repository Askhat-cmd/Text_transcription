# TASKLIST PRD-145: `answer_adaptive.py` Modularization (Wave 131)

## Status Legend
- [ ] pending
- [~] in progress
- [x] done

## Execution Log
- [x] Create `pricing_helpers.py` and move `_estimate_cost` + pricing table.
- [x] Create `fast_path_stage_helpers.py` and move `_run_fast_path_stage`.
- [x] Create `full_path_stage_helpers.py` and move `_run_full_path_llm_stage` + `_run_generation_and_success_stage`.
- [x] Rewrite `runtime_misc_helpers.py` into compatibility re-export facade.
- [x] Run targeted tests for runtime generation/validation/trace contracts.
- [x] Run full suite with local TMP/TEMP override.

## Result Snapshot
- `runtime_misc_helpers.py`: `652 -> 12` lines (compatibility facade).
- New modules:
  - `fast_path_stage_helpers.py`: `272` lines
  - `full_path_stage_helpers.py`: `354` lines
  - `pricing_helpers.py`: `43` lines
- Validation:
  - Targeted: `15 passed`
  - Full suite: `501 passed, 13 skipped`
