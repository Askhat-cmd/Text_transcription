# PRD-154 - Answer Adaptive Modularization (Wave 140)

## Context
`response_utils.py` still contained shared response helper implementations while other clusters had already been extracted into dedicated modules.

## Goal
Convert `response_utils.py` into a pure compatibility facade and move remaining shared helpers into a dedicated module.

## Scope
- Add `bot_agent/adaptive_runtime/response_common_helpers.py`.
- Move shared helpers from `response_utils.py`:
  - `_get_feedback_prompt_for_state`
  - `_serialize_state_analysis`
  - `_build_success_response`
  - `_build_fast_success_metadata`
  - `_build_full_success_metadata`
  - `_build_path_recommendation_if_enabled`
  - `_persist_turn`
  - `_save_session_summary_best_effort`
  - `_build_sources_from_blocks`
  - `_attach_debug_payload`
  - `_attach_success_observability`
- Rewrite `response_utils.py` as compatibility imports from:
  - `response_common_helpers.py`
  - `response_failure_helpers.py`
  - `response_success_helpers.py`

## Acceptance Criteria
1. `response_common_helpers.py` contains moved shared helpers.
2. `response_utils.py` remains import-compatible with previous callsites.
3. Targeted tests pass.
4. Full suite passes.
