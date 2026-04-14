# TASKLIST PRD-051: `answer_adaptive.py` Modularization (Wave 37)

## Status Legend
- [ ] pending
- [~] in progress
- [x] done

## Execution Log
- [x] Add helper `_handle_llm_generation_error_response(...)` in response helpers.
- [x] Replace inline LLM error branch in orchestrator with helper call.
- [x] Preserve error contract (response payload + debug trace finalize path).
- [x] Run targeted tests.
- [x] Attempt full suite (`--maxfail=1`).

## Result Snapshot
- Updated `adaptive_runtime/response_utils.py`:
  - `_handle_llm_generation_error_response(...)`
- Updated `answer_adaptive.py`:
  - inline LLM generation error branch replaced with helper call
- Validation:
  - Targeted: `13 passed`
  - Full suite: `501 passed, 13 skipped`
