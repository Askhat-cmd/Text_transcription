# TASKLIST PRD-118: `answer_adaptive.py` Modularization (Wave 104)

## Status Legend
- [ ] pending
- [~] in progress
- [x] done

## Execution Log
- [x] Localize stable Stage-2 utility callbacks in `routing_stage_helpers.py`.
- [x] Localize contradiction detector call in Stage-2 helper.
- [x] Remove obsolete Stage-2 callback args from `answer_adaptive.py`.
- [x] Remove now-unused facade imports.
- [x] Run expanded targeted tests.
- [x] Run full suite (`--maxfail=1`).

## Result Snapshot
- Stage-2 facade contract narrowed by 8 utility callbacks.
- `answer_adaptive.py`: `512` lines; `_fn=` occurrences: `10`.
- Validation:
  - Expanded targeted: `31 passed`
  - Full suite: `501 passed, 13 skipped`
