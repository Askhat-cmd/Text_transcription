# TASKLIST PRD-086: `answer_adaptive.py` Modularization (Wave 72)

## Status Legend
- [ ] pending
- [~] in progress
- [x] done

## Execution Log
- [x] Remove local function-injection parameter from `_build_retrieval_debug_details`.
- [x] Update retrieval observability call path to match simplified signature.
- [x] Run expanded targeted tests.
- [x] Run full suite (`--maxfail=1`).

## Result Snapshot
- Trace retrieval debug assembly contract simplified.
- Validation:
  - Expanded targeted: `31 passed`
  - Full suite: `501 passed, 13 skipped`
