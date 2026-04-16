# PRD-153 - Answer Adaptive Modularization (Wave 139)

## Context
After Wave 138 extraction, some runtime modules still imported moved failure helpers through `response_utils.py`.

## Goal
Align runtime callsites to direct imports from `response_failure_helpers.py`.

## Scope
- Update `answer_adaptive.py` import for `_build_unhandled_exception_response`.
- Update `full_path_stage_helpers.py` import for `_handle_llm_generation_error_response`.
- Update `retrieval_stage_helpers.py` import for `_run_no_retrieval_stage`.

## Acceptance Criteria
1. Direct imports use `response_failure_helpers.py`.
2. Compatibility layer remains in place for stability.
3. Targeted and full tests pass.
