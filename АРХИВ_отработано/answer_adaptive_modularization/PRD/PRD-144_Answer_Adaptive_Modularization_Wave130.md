# PRD-144: `answer_adaptive.py` Modularization (Wave 130)

## Context
`runtime_misc_helpers.py` still contained bootstrap/onboarding helpers mixed with generation stages. This keeps unrelated responsibilities in one file and complicates final cleanup waves.

## Scope (Wave 130)
Extract bootstrap/onboarding helpers into:
- `bot_agent/adaptive_runtime/bootstrap_runtime_helpers.py`

Moved functions:
- `_build_start_command_response`
- `_prepare_adaptive_run_context`
- `_load_runtime_memory_context`
- `_run_bootstrap_and_onboarding_guard`

## Objectives
1. Separate bootstrap responsibilities from generation/runtime stage orchestration.
2. Keep existing call signatures and behavior fully stable.
3. Preserve test green state after extraction.

## Technical Design
### Files
- `bot_agent/adaptive_runtime/bootstrap_runtime_helpers.py` (new)
- `bot_agent/adaptive_runtime/runtime_misc_helpers.py`

### Changes
- Move bootstrap helper implementations without logic changes.
- Import moved helpers back into `runtime_misc_helpers.py` (no callsite behavior changes).
- Remove now-redundant function bodies from `runtime_misc_helpers.py`.

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
