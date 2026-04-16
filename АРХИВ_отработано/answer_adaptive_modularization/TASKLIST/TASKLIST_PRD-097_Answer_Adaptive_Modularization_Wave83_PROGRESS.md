# TASKLIST PRD-097: `answer_adaptive.py` Modularization (Wave 83)

## Status Legend
- [ ] pending
- [~] in progress
- [x] done

## Execution Log
- [x] Localize Stage-4 full-path LLM-cycle helper dependencies in `runtime_misc_helpers.py`.
- [x] Remove obsolete Stage-4 call args in `answer_adaptive.py`.
- [x] Remove now-unused import in `answer_adaptive.py`.
- [x] Run expanded targeted tests.
- [x] Run full suite (`--maxfail=1`).

## Result Snapshot
- Stage-4 LLM-cycle contract narrowed.
- Validation:
  - Expanded targeted: `31 passed`
  - Full suite: `501 passed, 13 skipped`
