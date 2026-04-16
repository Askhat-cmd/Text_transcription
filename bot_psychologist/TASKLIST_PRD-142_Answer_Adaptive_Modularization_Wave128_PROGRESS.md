# TASKLIST PRD-142: `answer_adaptive.py` Modularization (Wave 128)

## Status Legend
- [ ] pending
- [~] in progress
- [x] done

## Execution Log
- [x] Create new module `adaptive_runtime/llm_runtime_helpers.py`.
- [x] Move LLM-cycle helper functions from `runtime_misc_helpers.py` into the new module.
- [x] Wire imports/calls in `runtime_misc_helpers.py` to moved helpers.
- [x] Remove now-unused typing imports from `runtime_misc_helpers.py`.
- [x] Run targeted tests for generation/validation/trace contracts.
- [x] Run full suite with local TMP/TEMP override.

## Result Snapshot
- `runtime_misc_helpers.py`: 1260 -> 915 lines.
- New module `llm_runtime_helpers.py`: 357 lines.
- Validation:
  - Targeted: `15 passed`
  - Full suite: `501 passed, 13 skipped`
