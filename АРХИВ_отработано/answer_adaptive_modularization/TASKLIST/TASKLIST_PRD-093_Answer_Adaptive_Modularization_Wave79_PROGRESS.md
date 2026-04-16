# TASKLIST PRD-093: `answer_adaptive.py` Modularization (Wave 79)

## Status Legend
- [ ] pending
- [~] in progress
- [x] done

## Execution Log
- [x] Localize `resolve_mode_prompt` and `build_mode_directive` dependencies inside retrieval runtime helper.
- [x] Remove obsolete Stage-3 parameters from retrieval helper contract.
- [x] Remove obsolete Stage-3 call arguments in `answer_adaptive.py`.
- [x] Run expanded targeted tests.
- [x] Run full suite (`--maxfail=1`).

## Result Snapshot
- Stage-3 contract reduced by two helper dependencies.
- Validation:
  - Expanded targeted: `31 passed`
  - Full suite: `501 passed, 13 skipped`
