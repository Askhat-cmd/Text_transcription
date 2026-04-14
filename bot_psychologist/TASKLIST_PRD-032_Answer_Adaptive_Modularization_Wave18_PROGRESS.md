# TASKLIST PRD-032: `answer_adaptive.py` Modularization (Wave 18)

## Status Legend
- [ ] pending
- [~] in progress
- [x] done

## Execution Log
- [x] Add helper `_build_state_context_mode_prompt(...)`.
- [x] Add helper `_build_phase8_context_suffix(...)`.
- [x] Replace duplicated phase8/context-mode blocks in fast/full branches of `answer_adaptive.py`.
- [x] Run targeted tests.
- [x] Run full suite.

## Result Snapshot
- Added in `adaptive_runtime/routing_stage_helpers.py`:
  - `_build_state_context_mode_prompt(...)`
  - `_build_phase8_context_suffix(...)`
- Replaced duplicated inline logic in `answer_adaptive.py` for:
  - fast-path phase8 suffix build
  - full-path phase8 suffix build
  - full-path informational state-context mode prompt
- Validation:
  - Targeted: `13 passed`
  - Full suite: `501 passed, 13 skipped`
