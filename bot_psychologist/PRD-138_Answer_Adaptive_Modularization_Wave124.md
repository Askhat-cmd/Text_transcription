# PRD-138: `answer_adaptive.py` Modularization (Wave 124)

## Context
`trace_helpers.py` still used legacy `*_fn` callable dependency naming in trace-finalization path, while upstream runtime modules had already moved to neutral callable names.

## Scope (Wave 124)
Normalize callable dependency contracts in trace finalization:
- `_apply_trace_memory_snapshot(...)`
- `_finalize_trace_payload(...)`
- `_finalize_success_debug_trace(...)`
- `_finalize_failure_debug_trace(...)`
- synchronize kwargs in `response_utils.py`

## Objectives
1. Align trace-helper contracts to the active naming convention.
2. Keep trace payload shape and runtime behavior unchanged.
3. Preserve full regression stability.

## Technical Design
### Files
- `bot_agent/adaptive_runtime/trace_helpers.py`
- `bot_agent/adaptive_runtime/response_utils.py`

### Changes
Rename dependency parameters:
- `build_state_trajectory_fn` -> `build_state_trajectory`
- `store_blob_fn` -> `store_blob`
- `compute_anomalies_fn` -> `compute_anomalies`
- `attach_trace_schema_fn` -> `attach_trace_schema`
- `strip_legacy_trace_fields_fn` -> `strip_legacy_trace_fields`
- `estimate_cost_fn` -> `estimate_cost`

And update all kwargs passed from `response_utils.py` (including `finalize_success_kwargs` payload).

No logic changes.

## Test Plan
Targeted:
- `tests/integration/test_generation_validation_separation.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_sparse_output_triggers_regeneration_hint.py`
- `tests/integration/test_degraded_mode_without_retrieval.py`
- `tests/test_retrieval_pipeline_simplified.py`
- `tests/regression/test_no_level_based_prompting.py`
- `tests/regression/test_trace_reflects_real_execution_only.py`
- `tests/unit/test_prompt_stack_order.py`
- `tests/contract/test_prompt_stack_contract_v2.py`

Full:
- `pytest -q`

