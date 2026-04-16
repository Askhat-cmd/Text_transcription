# PRD-147: `answer_adaptive.py` Modularization (Wave 133)

## Context
`routing_stage_helpers.py` remained a large mixed module (~677 lines) containing both:
- pre-routing classification/diagnostics orchestration
- routing-context/debug/practice wiring

## Scope (Wave 133)
Split `routing_stage_helpers.py` into focused modules:

1. `adaptive_runtime/routing_pre_stage_helpers.py`
- `_run_state_analysis_stage`
- `_compute_diagnostics_v1`
- `_build_contradiction_payload`
- `_resolve_pre_routing`
- `_run_state_and_pre_routing_pipeline`

2. `adaptive_runtime/routing_context_helpers.py`
- `INFORMATIONAL_MODE_PROMPT`
- `_apply_fast_path_debug_bootstrap`
- `_build_state_context_mode_prompt`
- `_build_phase8_context_suffix`
- `_build_fast_path_mode_directive`
- `_resolve_routing_and_apply_block_cap`
- `_resolve_practice_selection_context`
- `_attach_routing_stage_debug_trace`
- `_finalize_routing_context_and_trace`

3. Rewrite `adaptive_runtime/routing_stage_helpers.py` as compatibility façade re-exporting all previous symbols.

## Objectives
1. Reduce module complexity and isolate routing responsibilities.
2. Preserve all existing imports/contracts in runtime and tests.
3. Keep behavior unchanged.

## Test Plan
Targeted:
- `tests/integration/test_generation_validation_separation.py`
- `tests/integration/test_sparse_output_triggers_regeneration_hint.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/unit/test_query_is_passed_to_output_validation_policy_v1031.py`
- `tests/contract/test_prompt_stack_contract_v2.py`
- `tests/unit/test_prompt_stack_order.py`
- `tests/regression/test_trace_reflects_real_execution_only.py`
- `tests/regression/test_no_level_based_prompting.py`
- `tests/integration/test_degraded_mode_without_retrieval.py`
- `tests/test_retrieval_pipeline_simplified.py`

Full:
- `pytest -q` (with local TMP/TEMP override)
