# PRD-137: `answer_adaptive.py` Modularization (Wave 123)

## Context
`state_helpers.py` still used `*_fn` names for internal dependency injection (`build_state_context_fn`, `build_working_state_fn`) while adjacent runtime layers had already moved to neutral callable naming.

## Scope (Wave 123)
Normalize state-helper callable dependency names:
- `_compose_state_context(...)`
- `_set_working_state_best_effort(...)`
- synchronize callsites in:
  - `runtime_misc_helpers.py`
  - `retrieval_stage_helpers.py`

## Objectives
1. Align state-helper contracts with current naming convention.
2. Keep runtime behavior unchanged.
3. Preserve full regression stability.

## Technical Design
### Files
- `bot_agent/adaptive_runtime/state_helpers.py`
- `bot_agent/adaptive_runtime/runtime_misc_helpers.py`
- `bot_agent/adaptive_runtime/retrieval_stage_helpers.py`

### Changes
Rename parameters:
- `build_state_context_fn` -> `build_state_context`
- `build_working_state_fn` -> `build_working_state`

And update all keyword callsites accordingly.

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

