# TASKLIST PRD-044: `answer_adaptive.py` Modularization (Wave 30)

## Status Legend
- [ ] pending
- [~] in progress
- [x] done

## Execution Log
- [x] Add helper `_resolve_practice_selection_context(...)` in routing-stage helpers.
- [x] Replace inline practice-selection block in Stage 3 full-path flow.
- [x] Preserve practice metadata updates (`last_practice_channel`) and context suffix contract.
- [x] Run targeted tests.
- [x] Attempt full suite (environment-limited).

## Result Snapshot
- Updated `adaptive_runtime/routing_stage_helpers.py`:
  - `_resolve_practice_selection_context(...)`
- Updated `answer_adaptive.py`:
  - practice routing block replaced by helper call
- Validation:
  - Targeted: `13 passed`
  - Full suite: attempted, but blocked by host ACL/FS restrictions in this runtime
    (`PermissionError` around `%TEMP%\\pytest-of-Reklama-3D` and sandbox path access).
