# PRD-107: `answer_adaptive.py` Modularization (Wave 93)

## Context
Stage-4 success orchestration still received many pass-through dependencies from facade that are runtime-internal.

## Scope (Wave 93)
Localize Stage-4 success dependency wiring inside `runtime_misc_helpers.py` and narrow `answer_adaptive.py` call contract.

## Objectives
1. Reduce Stage-4 argument surface in facade without changing behavior.
2. Keep success response, metrics and trace wiring stable.
3. Validate with expanded targeted and full suites.

## Technical Design
Update `bot_agent/adaptive_runtime/runtime_misc_helpers.py`:
- narrow `_run_generation_and_success_stage(...)` signature by removing pass-through args:
  - `collect_llm_session_metrics_fn`
  - `update_session_token_metrics_fn`
  - `set_working_state_best_effort_fn`
  - `build_path_recommendation_if_enabled_fn`
  - `get_feedback_prompt_for_state_fn`
  - `persist_turn_fn`
  - `save_session_summary_best_effort_fn`
  - `build_full_path_success_response_fn`
- localize runtime imports and function binding:
  - `_collect_llm_session_metrics` (module-local)
  - `_update_session_token_metrics` (trace helpers)
  - `_set_working_state_best_effort` (state helpers)
  - `_build_path_recommendation_if_enabled`, `_get_feedback_prompt_for_state`, `_persist_turn`, `_save_session_summary_best_effort`, `_build_full_path_success_response` (response utils)

Update `bot_agent/answer_adaptive.py`:
- remove obsolete Stage-4 call args.
- drop now-unused imports tied to removed pass-throughs.

## Test Plan
Expanded targeted:
- `tests/regression/test_no_level_based_prompting.py`
- `tests/test_retrieval_pipeline_simplified.py`
- `tests/integration/test_degraded_mode_without_retrieval.py`
- `tests/e2e/test_degraded_retrieval_case.py`
- `tests/integration/test_sparse_output_triggers_regeneration_hint.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_routing_recalibration_for_exploratory_queries.py`
- `tests/integration/test_adaptive_stream_contract.py`
- `tests/test_sse_payload.py`
- `tests/unit/test_curious_not_auto_informational.py`
- `tests/unit/test_user_level_adapter_removed.py`
- `tests/unit/test_sd_legacy_final_cleanup_prompt_context.py`
- `tests/unit/test_query_is_passed_to_output_validation_policy_v1031.py`
- `tests/integration/test_generation_validation_separation.py`

Full:
- `pytest -q tests --maxfail=1`
