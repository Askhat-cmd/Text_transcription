# TASKLIST PRD-053: `answer_adaptive.py` Modularization (Wave 39)

## Status Legend
- [ ] pending
- [~] in progress
- [x] done

## Execution Log
- [x] Add helper `_run_llm_generation_cycle(...)` in runtime misc helpers.
- [x] Replace duplicated fast-path prompt-stack/preview/LLM generation block.
- [x] Replace duplicated full-path prompt-stack/preview/LLM generation block.
- [x] Preserve trace and prompt-stack contract.
- [x] Run targeted tests.
- [x] Attempt full suite (`--maxfail=1`).

## Result Snapshot
- Updated `adaptive_runtime/runtime_misc_helpers.py`:
  - `_run_llm_generation_cycle(...)`
- Updated `answer_adaptive.py`:
  - duplicated LLM generation preflight blocks replaced with helper calls
- Validation:
  - Targeted: `13 passed`
  - Full suite: `501 passed, 13 skipped`
