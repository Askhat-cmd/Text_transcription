# TASKLIST PRD-085: `answer_adaptive.py` Modularization (Wave 71)

## Status Legend
- [ ] pending
- [~] in progress
- [x] done

## Execution Log
- [x] Replace bootstrap onboarding callable flag with direct bool contract.
- [x] Replace routing cap callable flag with direct bool contract.
- [x] Update retrieval and orchestration callsites to compact bool-based APIs.
- [x] Run expanded targeted tests.
- [x] Run full suite (`--maxfail=1`).

## Result Snapshot
- Removed lambda wrappers for informational branch flag in two runtime boundaries.
- Validation:
  - Expanded targeted: `31 passed`
  - Full suite: `501 passed, 13 skipped`
