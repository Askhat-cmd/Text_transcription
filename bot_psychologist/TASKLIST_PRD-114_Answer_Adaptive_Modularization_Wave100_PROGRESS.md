# TASKLIST PRD-114: `answer_adaptive.py` Modularization (Wave 100)

## Status Legend
- [ ] pending
- [~] in progress
- [x] done

## Execution Log
- [x] Localize output-validation policy adapter in fast-path stage helper.
- [x] Localize output-validation policy adapter in full-path generation stage helper.
- [x] Remove obsolete callback pass-through args in `answer_adaptive.py`.
- [x] Preserve validation toggle contract via `force_enabled=output_validation_enabled`.
- [x] Run expanded targeted tests.
- [x] Run full suite (`--maxfail=1`).

## Result Snapshot
- Facade contract narrowed by 2 callback args.
- `answer_adaptive.py`: `537` lines; `_fn=` occurrences: `23`.
- Validation:
  - Expanded targeted: `31 passed`
  - Full suite: `501 passed, 13 skipped`
