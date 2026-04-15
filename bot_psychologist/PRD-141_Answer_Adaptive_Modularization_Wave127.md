# PRD-141: `answer_adaptive.py` Modularization (Wave 127)

## Context
After Wave 126, the only remaining legacy callable-suffix in active runtime/facade contracts was `generate_retry_fn` within output-validation policy wiring.

## Scope (Wave 127)
Rename output-validation retry callable contract:
- `generate_retry_fn` -> `generate_retry`

Update all active callsites and affected tests:
- `bot_agent/adaptive_runtime/mode_policy_helpers.py`
- `bot_agent/adaptive_runtime/runtime_misc_helpers.py`
- `bot_agent/answer_adaptive.py`
- integration/unit tests covering output-validation policy behavior

## Objectives
1. Remove the last legacy `*_fn` contract in active adaptive runtime/facade path.
2. Keep output-validation behavior unchanged.
3. Preserve full regression stability.

## Technical Design
### Files
- `bot_agent/adaptive_runtime/mode_policy_helpers.py`
- `bot_agent/adaptive_runtime/runtime_misc_helpers.py`
- `bot_agent/answer_adaptive.py`
- `tests/unit/test_query_is_passed_to_output_validation_policy_v1031.py`
- `tests/integration/test_generation_validation_separation.py`
- `tests/integration/test_sparse_output_triggers_regeneration_hint.py`

### Changes
- Contract/key rename: `generate_retry_fn` -> `generate_retry`
- Adapter passthrough and all direct callsites synchronized.
- Test call signatures updated accordingly.

No logic changes.

## Test Plan
Targeted:
- `tests/unit/test_query_is_passed_to_output_validation_policy_v1031.py`
- `tests/integration/test_generation_validation_separation.py`
- `tests/integration/test_sparse_output_triggers_regeneration_hint.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_degraded_mode_without_retrieval.py`
- `tests/test_retrieval_pipeline_simplified.py`
- `tests/regression/test_no_level_based_prompting.py`
- `tests/regression/test_trace_reflects_real_execution_only.py`
- `tests/unit/test_prompt_stack_order.py`
- `tests/contract/test_prompt_stack_contract_v2.py`

Full:
- `pytest -q`

