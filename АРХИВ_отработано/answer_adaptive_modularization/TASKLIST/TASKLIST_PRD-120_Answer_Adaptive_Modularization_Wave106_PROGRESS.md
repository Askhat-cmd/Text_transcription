# TASKLIST PRD-120: `answer_adaptive.py` Modularization (Wave 106)

## Status Legend
- [ ] pending
- [~] in progress
- [x] done

## Execution Log
- [x] Rename bootstrap memory callback arg to neutral contract name.
- [x] Rename Stage-2 routing/state callback arg names to neutral contract names.
- [x] Rename Stage-3 retrieval callback arg names to neutral contract names.
- [x] Update facade Stage-1/2/3 callsites in `answer_adaptive.py`.
- [x] Run targeted tests.
- [x] Run full suite.

## Result Snapshot
- Contract naming standardized for Stage-1/2/3 external dependencies.
- `answer_adaptive.py`: `474` lines; `_fn=` occurrences: `2` (`generate_retry_fn` only).
- Validation:
  - Targeted: `13 passed`
  - Full suite: `501 passed, 13 skipped`
