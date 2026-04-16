# TASKLIST PRD-105: `answer_adaptive.py` Modularization (Wave 91)

## Status Legend
- [ ] pending
- [~] in progress
- [x] done

## Execution Log
- [x] Localize LLM-error failure-finalization dependencies in `response_utils.py (removed in Wave 142)`.
- [x] Remove obsolete Stage-4 DI args in `runtime_misc_helpers.py`.
- [x] Remove obsolete Stage-4 call args/import in `answer_adaptive.py`.
- [x] Run expanded targeted tests.
- [x] Run full suite (`--maxfail=1`).

## Result Snapshot
- Stage-4 LLM-error contract narrowed.
- Validation:
  - Expanded targeted: `31 passed`
  - Full suite: `501 passed, 13 skipped`

