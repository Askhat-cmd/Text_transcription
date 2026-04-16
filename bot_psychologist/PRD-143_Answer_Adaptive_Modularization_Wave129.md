# PRD-143: `answer_adaptive.py` Modularization (Wave 129)

## Context
After Wave 128, `runtime_misc_helpers.py` still contains small adapter-factory utilities that are infrastructure-level helpers rather than runtime stage logic.

## Scope (Wave 129)
Extract adapter factories from `runtime_misc_helpers.py` into:
- `bot_agent/adaptive_runtime/runtime_adapter_helpers.py`

Moved functions:
- `_build_output_validation_policy_adapter`
- `_build_runtime_output_validation_policy_adapter`
- `_build_set_working_state_best_effort_adapter`

## Objectives
1. Keep `runtime_misc_helpers.py` focused on stage orchestration.
2. Isolate reusable adapter wiring in a dedicated helper module.
3. Preserve behavior and compatibility.

## Technical Design
### Files
- `bot_agent/adaptive_runtime/runtime_adapter_helpers.py` (new)
- `bot_agent/adaptive_runtime/runtime_misc_helpers.py`

### Changes
- Move adapter factory implementations without behavior changes.
- Import moved helpers into `runtime_misc_helpers.py`.
- Keep all call signatures and callsites unchanged.

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
