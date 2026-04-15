# PRD-140: `answer_adaptive.py` Modularization (Wave 126)

## Context
After Wave 125, `runtime_misc_helpers.py` still had a few local/parameter naming leftovers (`*_fn`) in full-path orchestration despite contract cleanup in adjacent modules.

## Scope (Wave 126)
Normalize remaining local/parameter callable names in `runtime_misc_helpers.py`:
- local adapters:
  - `set_working_state_best_effort_fn` -> `set_working_state_best_effort`
- call wiring:
  - `apply_output_validation_policy_fn` -> `apply_output_validation_policy`

## Objectives
1. Complete consistency of callable naming in `runtime_misc_helpers`.
2. Keep runtime behavior unchanged.
3. Preserve full regression stability.

## Technical Design
### File
- `bot_agent/adaptive_runtime/runtime_misc_helpers.py`

### Changes
- Renamed local adapter variables and one call argument key in full-path flow.
- Kept `generate_retry_fn` untouched because it is part of output-validation adapter contract.

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

