# PRD-148: `answer_adaptive.py` Modularization (Wave 134)

## Context
After Wave 133, `routing_stage_helpers.py` became a faГ§ade. Some runtime modules still imported through old faГ§ade paths or imported `_estimate_cost` via `runtime_misc_helpers`.

## Scope (Wave 134)
Directly align imports with newly extracted modules:

1. `fast_path_stage_helpers.py`
- switch imports from `routing_stage_helpers` to `routing_context_helpers`

2. `retrieval_stage_helpers.py`
- switch imports from `routing_stage_helpers` to `routing_context_helpers`
- switch `_estimate_cost` import from `runtime_misc_helpers` to `pricing_helpers`

3. `response_utils.py (removed in Wave 142)`
- switch `_estimate_cost` imports from `runtime_misc_helpers` to `pricing_helpers`

## Objectives
1. Reduce legacy indirection in active runtime path.
2. Keep behavior unchanged.
3. Preserve compatibility faГ§ade for external callers/tests.

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

