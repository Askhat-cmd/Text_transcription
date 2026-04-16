# PRD-095: `answer_adaptive.py` Modularization (Wave 81)

## Context
Stage-3 still accepted a large set of operational function dependencies for no-retrieval fallback path. These dependencies are internal runtime helpers and can be localized inside retrieval runtime helper module.

## Scope (Wave 81)
Localize no-retrieval operational dependencies in `_run_retrieval_routing_context_stage(...)`.

## Objectives
1. Reduce Stage-3 contract noise in `answer_adaptive.py`.
2. Preserve no-retrieval fallback behavior and trace/error contracts.
3. Validate with expanded targeted and full test suites.

## Technical Design
Update `bot_agent/adaptive_runtime/retrieval_stage_helpers.py`:
- remove Stage-3 params:
  - `set_working_state_best_effort_fn`
  - `persist_turn_fn`
  - `finalize_failure_debug_trace_fn`
  - `estimate_cost_fn`
  - `compute_anomalies_fn`
  - `attach_trace_schema_fn`
  - `build_state_trajectory_fn`
  - `store_blob_fn`
- localize imports for no-retrieval fallback call:
  - `_run_no_retrieval_stage`, `_persist_turn`
  - `_set_working_state_best_effort`, `_estimate_cost`
  - `_build_working_state`
  - `_finalize_failure_debug_trace`
  - `_compute_anomalies`, `_build_state_trajectory`, `_store_blob`
  - `attach_trace_schema_status`
- wire these localized helpers into `_run_no_retrieval_stage(...)` call.

Update `bot_agent/answer_adaptive.py`:
- remove obsolete Stage-3 call arguments listed above.

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
