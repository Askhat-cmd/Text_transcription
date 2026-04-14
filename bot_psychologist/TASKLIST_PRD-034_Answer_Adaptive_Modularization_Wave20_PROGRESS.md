# TASKLIST PRD-034: `answer_adaptive.py` Modularization (Wave 20)

## Status Legend
- [ ] pending
- [~] in progress
- [x] done

## Execution Log
- [x] Add helper `_prepare_llm_prompt_previews(...)` in trace helpers.
- [x] Replace duplicated prompt preview blocks in fast/full branches.
- [x] Preserve compatibility export `_build_llm_prompts` in `answer_adaptive.py`.
- [x] Run targeted tests.
- [x] Run full suite.

## Result Snapshot
- Added in `adaptive_runtime/trace_helpers.py`:
  - `_prepare_llm_prompt_previews(...)`
- Updated `answer_adaptive.py`:
  - unified preview generation in fast/full branches
  - retained `_build_llm_prompts` import for regression compatibility
- Validation:
  - Targeted: `13 passed`
  - Full suite: `501 passed, 13 skipped`
