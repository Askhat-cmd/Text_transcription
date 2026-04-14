# TASKLIST PRD-091: `answer_adaptive.py` Modularization (Wave 77)

## Status Legend
- [ ] pending
- [~] in progress
- [x] done

## Execution Log
- [x] Localize hybrid-query builder dependencies inside retrieval runtime helper.
- [x] Remove obsolete `recent_user_turns_fn` and `hybrid_query_builder_cls` from Stage-3 contracts.
- [x] Clean up `answer_adaptive.py` imports and Stage-3 args.
- [x] Run expanded targeted tests.
- [x] Run full suite (`--maxfail=1`).

## Result Snapshot
- Stage-3 contract reduced by two dependencies.
- Validation:
  - Expanded targeted: `31 passed`
  - Full suite: `501 passed, 13 skipped`
