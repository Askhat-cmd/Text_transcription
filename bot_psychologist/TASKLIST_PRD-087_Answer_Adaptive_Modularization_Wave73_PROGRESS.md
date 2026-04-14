# TASKLIST PRD-087: `answer_adaptive.py` Modularization (Wave 73)

## Status Legend
- [ ] pending
- [~] in progress
- [x] done

## Execution Log
- [x] Localize author-intent detection dependency inside retrieval runtime helper.
- [x] Remove `detect_author_intent_fn` from Stage-3 helper contracts and callsites.
- [x] Clean up now-unused imports.
- [x] Run expanded targeted tests.
- [x] Run full suite (`--maxfail=1`).

## Result Snapshot
- Stage-3 contract reduced by one dependency boundary.
- Validation:
  - Expanded targeted: `31 passed`
  - Full suite: `501 passed, 13 skipped`
