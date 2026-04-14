# TASKLIST PRD-083: `answer_adaptive.py` Modularization (Wave 69)

## Status Legend
- [ ] pending
- [~] in progress
- [x] done

## Execution Log
- [x] Remove internal function-injection parameters from Stage-3 runtime helpers.
- [x] Replace helper injection with direct module-local calls in retrieval helpers.
- [x] Switch Stage-3 call in `answer_adaptive.py` to new compact contract.
- [x] Remove now-unused retrieval helper imports in `answer_adaptive.py`.
- [x] Run expanded targeted tests.
- [x] Run full suite (`--maxfail=1`).

## Result Snapshot
- Stage-3 helper contract reduced, behavior preserved.
- Validation:
  - Expanded targeted: `31 passed`
  - Full suite: `501 passed, 13 skipped`
