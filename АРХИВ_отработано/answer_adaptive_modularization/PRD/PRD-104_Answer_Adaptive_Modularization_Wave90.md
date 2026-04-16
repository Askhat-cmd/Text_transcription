# PRD-104: `answer_adaptive.py` Modularization (Wave 90)

## Context
Unhandled-exception path in `answer_adaptive.py` still passed many runtime-internal DI helpers into `_build_unhandled_exception_response(...)`.

## Scope (Wave 90)
Narrow unhandled-exception contract by localizing error/debug-finalization internals inside `response_utils.py (removed in Wave 142)`.

## Objectives
1. Reduce facade `except`-branch argument surface.
2. Preserve error response payload and debug trace fallback behavior.
3. Validate with expanded targeted and full suites.

## Technical Design
Update `bot_agent/adaptive_runtime/response_utils.py (removed in Wave 142)`:
- narrow `_build_unhandled_exception_response(...)` signature by removing DI params:
  - `build_error_response_fn`
  - `get_conversation_memory_fn`
  - `persist_turn_best_effort_fn`
  - `finalize_failure_debug_trace_fn`
  - `estimate_cost_fn`
  - `compute_anomalies_fn`
  - `attach_trace_schema_fn`
  - `build_state_trajectory_fn`
  - `store_blob_fn`
  - `strip_legacy_trace_fields_fn`
- localize imports and direct calls:
  - `get_conversation_memory`, `attach_trace_schema_status`
  - `_persist_turn_best_effort`, `_build_error_response`
  - `_finalize_failure_debug_trace`, `_strip_legacy_trace_fields`
  - `_estimate_cost`, `_compute_anomalies`, `_build_state_trajectory`, `_store_blob`
- keep behavior unchanged (best-effort persistence/debug-finalization).

Update `bot_agent/answer_adaptive.py`:
- remove obsolete `except` call args.
- remove now-unused facade imports tied to removed args.

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

