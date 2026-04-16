# PRD-105: `answer_adaptive.py` Modularization (Wave 91)

## Context
Stage-4 LLM error path still passed failure-finalization DI helpers across facade/runtime boundaries.

## Scope (Wave 91)
Narrow LLM-error helper contract by localizing failure-finalization internals inside `response_utils.py (removed in Wave 142)`.

## Objectives
1. Reduce Stage-4 argument surface in `answer_adaptive.py`.
2. Keep LLM-error response/debug behavior unchanged.
3. Validate with expanded targeted and full test suites.

## Technical Design
Update `bot_agent/adaptive_runtime/response_utils.py (removed in Wave 142)`:
- narrow `_handle_llm_generation_error_response(...)` signature by removing DI params:
  - `finalize_failure_debug_trace_fn`
  - `estimate_cost_fn`
  - `compute_anomalies_fn`
  - `attach_trace_schema_fn`
  - `build_state_trajectory_fn`
  - `store_blob_fn`
- localize runtime imports and direct calls:
  - `_finalize_failure_debug_trace`
  - `_estimate_cost`, `_compute_anomalies`, `_build_state_trajectory`, `_store_blob`
  - `attach_trace_schema_status`

Update `bot_agent/adaptive_runtime/runtime_misc_helpers.py`:
- remove removed DI params from `_run_full_path_llm_stage(...)`.
- remove removed DI params from `_run_generation_and_success_stage(...)` and call-site bridge.

Update `bot_agent/answer_adaptive.py`:
- remove obsolete Stage-4 call args.
- remove now-unused facade import `_finalize_failure_debug_trace`.

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

