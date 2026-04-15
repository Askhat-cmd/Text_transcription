# PRD-112: `answer_adaptive.py` Modularization (Wave 98)

## Context
Fast-path Stage-2 still received multiple runtime-stable callbacks from facade, although those dependencies can be localized inside `runtime_misc_helpers.py`.

## Scope (Wave 98)
Localize fast-path success-response dependencies in `runtime_misc_helpers.py` and remove obsolete pass-through args from `answer_adaptive.py`.

## Objectives
1. Reduce fast-path Stage-2 argument surface in `answer_adaptive.py`.
2. Keep fast-path behavior and observability unchanged.
3. Validate via expanded targeted and full test suites.

## Technical Design
Update `bot_agent/adaptive_runtime/runtime_misc_helpers.py`:
- remove `_run_fast_path_stage(...)` args:
  - `set_working_state_best_effort_fn`
  - `collect_llm_session_metrics_fn`
  - `update_session_token_metrics_fn`
  - `persist_turn_fn`
  - `get_feedback_prompt_for_state_fn`
  - `estimate_cost_fn`
  - `compute_anomalies_fn`
  - `attach_trace_schema_fn`
  - `build_state_trajectory_fn`
  - `store_blob_fn`
- localize runtime imports and wiring for these call paths.

Update `bot_agent/answer_adaptive.py`:
- remove obsolete fast-path call args listed above.
- remove now-unused facade imports/lambdas tied to removed pass-throughs.

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
