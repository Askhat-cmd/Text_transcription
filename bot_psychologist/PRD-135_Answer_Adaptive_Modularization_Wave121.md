# PRD-135: `answer_adaptive.py` Modularization (Wave 121)

## Context
Core generation/validation helpers in `runtime_misc_helpers.py` still mixed legacy `*_fn` callable names with newer neutral-style dependency names. This reduced consistency across recent modularization waves.

## Scope (Wave 121)
Normalize callable dependency names in generation/validation core:
- `_generate_llm_with_trace(...)`
- `_collect_llm_session_metrics(...)`
- `_run_llm_generation_cycle(...)`
- `_format_and_validate_llm_answer(...)`
- synchronize callsites in `runtime_misc_helpers.py` and `response_utils.py`

## Objectives
1. Align dependency contracts to neutral naming in core runtime path.
2. Keep behavior and response contracts unchanged.
3. Preserve full regression stability.

## Technical Design
### Files
- `bot_agent/adaptive_runtime/runtime_misc_helpers.py`
- `bot_agent/adaptive_runtime/response_utils.py`

### Changes
Renamed selected contracts:
- `build_llm_call_trace_fn` -> `build_llm_call_trace`
- `update_session_token_metrics_fn` -> `update_session_token_metrics`
- `build_prompt_stack_override_fn` -> `build_prompt_stack_override`
- `prepare_llm_prompt_previews_fn` -> `prepare_llm_prompt_previews`
- `generate_llm_with_trace_fn` -> `generate_llm_with_trace`
- `run_validation_retry_generation_fn` -> `run_validation_retry_generation`
- `apply_output_validation_policy_fn` -> `apply_output_validation_policy`
- `apply_output_validation_observability_fn` -> `apply_output_validation_observability`

And synchronized the corresponding keyword arguments at callsites.

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

