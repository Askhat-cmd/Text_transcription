# PRD-133: `answer_adaptive.py` Modularization (Wave 119)

## Context
Success-path observability helpers still had mixed callable contract naming (`*_fn`) in fast/full response builders and in runtime callsites. This reduced readability and consistency with the naming standard introduced in recent waves.

## Scope (Wave 119)
Normalize selected observability callable contracts:
- `_attach_success_observability(...)`
- `_build_fast_path_success_response(...)`
- `_build_full_path_success_response(...)`
- `_run_full_path_success_stage(...)`
- callsites in `runtime_misc_helpers.py`

## Objectives
1. Unify callable dependency naming in success observability path.
2. Keep behavior and response contracts unchanged.
3. Preserve full regression stability.

## Technical Design
### Files
- `bot_agent/adaptive_runtime/response_utils.py (removed in Wave 142)`
- `bot_agent/adaptive_runtime/runtime_misc_helpers.py`

### Changes
Rename selected callable params to neutral names:
- `attach_success_observability_fn` -> `attach_success_observability`
- `strip_legacy_runtime_metadata_fn` -> `strip_legacy_runtime_metadata`
- `attach_debug_payload_fn` -> `attach_debug_payload`
- `finalize_success_debug_trace_fn` -> `finalize_success_debug_trace`
- `estimate_cost_fn` -> `estimate_cost`
- `compute_anomalies_fn` -> `compute_anomalies`
- `attach_trace_schema_fn` -> `attach_trace_schema`
- `build_state_trajectory_fn` -> `build_state_trajectory`
- `store_blob_fn` -> `store_blob`
- `strip_legacy_trace_fields_fn` -> `strip_legacy_trace_fields`

Note:
- Internal kwargs passed into trace finalizer remain with legacy key names (`*_fn`) where required by downstream function signatures.

## Test Plan
Targeted:
- `tests/integration/test_generation_validation_separation.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_sparse_output_triggers_regeneration_hint.py`
- `tests/integration/test_degraded_mode_without_retrieval.py`
- `tests/test_retrieval_pipeline_simplified.py`
- `tests/regression/test_no_level_based_prompting.py`
- `tests/regression/test_trace_reflects_real_execution_only.py`

Full:
- `pytest -q`


