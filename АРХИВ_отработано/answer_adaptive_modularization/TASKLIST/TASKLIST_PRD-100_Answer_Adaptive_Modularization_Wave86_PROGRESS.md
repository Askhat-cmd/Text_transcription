# TASKLIST PRD-100: `answer_adaptive.py` Modularization (Wave 86)

## Status Legend
- [ ] pending
- [~] in progress
- [x] done

## Execution Log
- [x] Localize onboarding instruction builders in fast-path runtime stage.
- [x] Remove obsolete fast-path call args in `answer_adaptive.py`.
- [x] Remove now-unused onboarding imports in `answer_adaptive.py`.
- [x] Run expanded targeted tests.
- [x] Run full suite (`--maxfail=1`).

## Result Snapshot
- Fast-path onboarding-builder contract narrowed.
- Validation:
  - Expanded targeted: `31 passed`
  - Full suite: `501 passed, 13 skipped`
