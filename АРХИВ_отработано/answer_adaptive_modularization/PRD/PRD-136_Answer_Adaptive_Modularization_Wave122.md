# PRD-136: `answer_adaptive.py` Modularization (Wave 122)

## Context
`routing_stage_helpers.py` and its retrieval/fast-path callsites still contained mixed `*_fn` callable dependency names, while adjacent runtime modules already moved to neutral naming style.

## Scope (Wave 122)
Normalize callable dependency contracts for routing-context assembly and block-cap routing:
- `_build_phase8_context_suffix(...)`
- `_build_fast_path_mode_directive(...)`
- `_resolve_routing_and_apply_block_cap(...)`
- `_attach_routing_stage_debug_trace(...)`
- `_finalize_routing_context_and_trace(...)`
- synchronize callsites in:
  - `retrieval_stage_helpers.py`
  - `runtime_misc_helpers.py`

## Objectives
1. Align routing/retrieval helper contracts with current neutral naming standard.
2. Keep routing logic and debug-trace behavior unchanged.
3. Preserve full regression stability.

## Technical Design
### Files
- `bot_agent/adaptive_runtime/routing_stage_helpers.py`
- `bot_agent/adaptive_runtime/retrieval_stage_helpers.py`
- `bot_agent/adaptive_runtime/runtime_misc_helpers.py`

### Changes
Renamed selected parameters, including:
- `build_mode_directive_fn` -> `build_mode_directive`
- `resolve_mode_prompt_fn` -> `resolve_mode_prompt`
- `log_retrieval_pairs_fn` -> `log_retrieval_pairs`
- `build_first_turn_instruction_fn` -> `build_first_turn_instruction`
- `build_mixed_query_instruction_fn` -> `build_mixed_query_instruction`
- `build_user_correction_instruction_fn` -> `build_user_correction_instruction`
- `build_informational_guardrail_instruction_fn` -> `build_informational_guardrail_instruction`
- `truncate_preview_fn` -> `truncate_preview`
- `refresh_context_and_apply_trace_snapshot_fn` -> `refresh_context_and_apply_trace_snapshot`

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

