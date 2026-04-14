# TASKLIST PRD-084: `answer_adaptive.py` Modularization (Wave 70)

## Status Legend
- [ ] pending
- [~] in progress
- [x] done

## Execution Log
- [x] Simplify trace observability helpers to use trace-local debug builders.
- [x] Remove Stage-3 debug-builder injection params from retrieval runtime helper contracts.
- [x] Compact Stage-3 call in `answer_adaptive.py` and clean imports.
- [x] Run expanded targeted tests.
- [x] Run full suite (`--maxfail=1`).

## Result Snapshot
- Stage-3 retrieval/trace path contracts reduced.
- Validation:
  - Expanded targeted: `31 passed`
  - Full suite: `501 passed, 13 skipped`
