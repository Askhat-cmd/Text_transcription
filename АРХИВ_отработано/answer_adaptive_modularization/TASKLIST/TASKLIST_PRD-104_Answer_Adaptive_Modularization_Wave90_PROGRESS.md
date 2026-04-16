# TASKLIST PRD-104: `answer_adaptive.py` Modularization (Wave 90)

## Status Legend
- [ ] pending
- [~] in progress
- [x] done

## Execution Log
- [x] Localize unhandled-exception helper dependencies in `response_utils.py (removed in Wave 142)`.
- [x] Remove obsolete `except` call args in `answer_adaptive.py`.
- [x] Remove now-unused facade imports tied to error path.
- [x] Run expanded targeted tests.
- [x] Run full suite (`--maxfail=1`).

## Result Snapshot
- Unhandled-exception contract narrowed.
- Validation:
  - Expanded targeted: `31 passed`
  - Full suite: `501 passed, 13 skipped`

