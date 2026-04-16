# PRD-152 - Answer Adaptive Modularization (Wave 138)

## Context
After Wave 136/137, `response_utils.py` still mixed success helpers with failure/no-retrieval handling.

## Goal
Extract failure/no-retrieval response orchestration into a dedicated module while preserving behavior and compatibility.

## Scope
- Add `bot_agent/adaptive_runtime/response_failure_helpers.py`.
- Move from `response_utils.py`:
  - `_build_partial_response`
  - `_build_error_response`
  - `_persist_turn_best_effort`
  - `_handle_no_retrieval_partial_response`
  - `_run_no_retrieval_stage`
  - `_handle_llm_generation_error_response`
  - `_build_unhandled_exception_response`
- Keep compatibility exports in `response_utils.py` via imports.

## Acceptance Criteria
1. Moved functions live in `response_failure_helpers.py`.
2. `response_utils.py` is reduced and still exposes previous callable names.
3. Targeted and full tests pass.
