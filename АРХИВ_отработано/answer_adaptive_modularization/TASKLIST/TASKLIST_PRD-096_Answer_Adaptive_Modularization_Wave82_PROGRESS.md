# TASKLIST PRD-096: `answer_adaptive.py` Modularization (Wave 82)

## Status Legend
- [ ] pending
- [~] in progress
- [x] done

## Execution Log
- [x] Remove obsolete Stage-4 DI params in `_run_generation_and_success_stage`.
- [x] Localize Stage-4 internal calls to full-path llm/success helpers.
- [x] Remove obsolete Stage-4 call args and dead imports in `answer_adaptive.py`.
- [x] Run expanded targeted tests.
- [x] Run full suite (`--maxfail=1`).

## Result Snapshot
- Stage-4 contract narrowed.
- Validation:
  - Expanded targeted: `31 passed`
  - Full suite: `501 passed, 13 skipped`
