# TASKLIST PRD-098: `answer_adaptive.py` Modularization (Wave 84)

## Status Legend
- [ ] pending
- [~] in progress
- [x] done

## Execution Log
- [x] Localize fast-path internal LLM-cycle helper dependencies in `runtime_misc_helpers.py`.
- [x] Remove obsolete fast-path call args in `answer_adaptive.py`.
- [x] Remove now-unused imports in `answer_adaptive.py`.
- [x] Restore compatibility export `_build_llm_prompts` in `answer_adaptive.py` for regression test contract.
- [x] Run expanded targeted tests.
- [x] Run full suite (`--maxfail=1`).

## Result Snapshot
- Fast-path contract narrowed while preserving class injection points.
- Validation:
  - Expanded targeted: `31 passed`
  - Full suite: `501 passed, 13 skipped`
