# TASKLIST PRD-141: `answer_adaptive.py` Modularization (Wave 127)

## Status Legend
- [ ] pending
- [~] in progress
- [x] done

## Execution Log
- [x] Rename output-validation retry contract `generate_retry_fn` -> `generate_retry` in runtime/helpers/facade.
- [x] Update affected integration/unit tests to new contract key.
- [x] Run targeted tests including updated validation-policy tests.
- [x] Run full suite with local TMP/TEMP override.

## Result Snapshot
- Last legacy `*_fn` contract removed from active adaptive runtime/facade flow.
- Behavior unchanged.
- Validation:
  - Targeted: `15 passed`
  - Full suite: `501 passed, 13 skipped`

