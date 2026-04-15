# PRD-132: `answer_adaptive.py` Modularization (Wave 118)

## Context
No-retrieval failure path still used legacy `*_fn` naming in callable contracts across stage helpers and callsites, reducing readability consistency versus recent waves.

## Scope (Wave 118)
Normalize selected callable contract names for no-retrieval path:
- `_handle_no_retrieval_partial_response(...)`
- `_run_no_retrieval_stage(...)`
- callsite wiring in `retrieval_stage_helpers.py`

## Objectives
1. Align no-retrieval contracts with neutral naming convention.
2. Preserve degraded/no-retrieval behavior and trace contracts.
3. Keep regression suite fully green.

## Technical Design
### Files
- `bot_agent/adaptive_runtime/response_utils.py`
- `bot_agent/adaptive_runtime/retrieval_stage_helpers.py`

### Changes
Rename selected parameters:
- `set_working_state_best_effort_fn` -> `set_working_state_best_effort`
- `persist_turn_fn` -> `persist_turn`
- `finalize_failure_debug_trace_fn` -> `finalize_failure_debug_trace`
- `estimate_cost_fn` -> `estimate_cost`
- `compute_anomalies_fn` -> `compute_anomalies`
- `attach_trace_schema_fn` -> `attach_trace_schema`
- `build_state_trajectory_fn` -> `build_state_trajectory`
- `store_blob_fn` -> `store_blob`

No logic changes.

## Test Plan
Targeted:
- `tests/integration/test_degraded_mode_without_retrieval.py`
- `tests/integration/test_generation_validation_separation.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_sparse_output_triggers_regeneration_hint.py`
- `tests/test_retrieval_pipeline_simplified.py`
- `tests/regression/test_no_level_based_prompting.py`
- `tests/regression/test_trace_reflects_real_execution_only.py`

Full:
- `pytest -q`

