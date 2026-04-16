# PRD-150 - Answer Adaptive Modularization (Wave 136)

## Context
`response_utils.py (removed in Wave 142)` still contained large full/fast success-stage orchestration blocks, making the module harder to navigate and slower for future cleanup waves.

## Goal
Extract success-stage orchestration into a dedicated module while preserving runtime behavior and external compatibility.

## Scope
- Add `bot_agent/adaptive_runtime/response_success_helpers.py`
- Move success-stage helper functions from `response_utils.py (removed in Wave 142)` into the new module:
  - `_build_fast_path_success_response`
  - `_build_full_path_success_response`
  - `_prepare_full_path_post_llm_artifacts`
  - `_finalize_full_path_success_stage`
  - `_run_full_path_success_stage`
- Keep `response_utils.py (removed in Wave 142)` as compatibility surface by importing moved helpers.

## Non-Goals
- Behavior changes in generation/routing logic.
- Any prompt/policy modifications.

## Acceptance Criteria
1. Moved helpers are defined in `response_success_helpers.py`.
2. `response_utils.py (removed in Wave 142)` no longer contains moved function bodies and re-exports them via imports.
3. Targeted tests pass.
4. Full test suite passes.

