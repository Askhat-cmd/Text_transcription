# TASKLIST PRD-046: `answer_adaptive.py` Modularization (Wave 32)

## Status Legend
- [ ] pending
- [~] in progress
- [x] done

## Execution Log
- [x] Add helper `_build_path_recommendation_if_enabled(...)` in response helpers.
- [x] Replace inline Stage 6 path recommendation block in `answer_adaptive.py`.
- [x] Preserve route-based path suppression contract.
- [x] Run targeted tests.
- [x] Attempt full suite (environment-limited).

## Result Snapshot
- Updated `adaptive_runtime/response_utils.py (removed in Wave 142)`:
  - `_build_path_recommendation_if_enabled(...)`
- Updated `answer_adaptive.py`:
  - inline path recommendation block replaced with helper call
- Validation:
  - Targeted: `13 passed`
  - Full suite: attempted with `--maxfail=1`, blocked by pytest temp-root ACL
    issue in host environment (`OSError` under `%TEMP%\\pytest-of-Reklama-3D`).

