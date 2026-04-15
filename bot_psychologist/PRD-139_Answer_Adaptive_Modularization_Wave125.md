# PRD-139: `answer_adaptive.py` Modularization (Wave 125)

## Context
Fast-path debug bootstrap in `routing_stage_helpers.py` still used legacy `*_fn` dependency names, while neighboring modularized helpers already used neutral callable names.

## Scope (Wave 125)
Normalize callable dependency names in fast-path debug bootstrap:
- `_apply_fast_path_debug_bootstrap(...)`
- synchronize callsite in `runtime_misc_helpers.py`

## Objectives
1. Remove remaining legacy naming in fast-path bootstrap dependencies.
2. Keep trace/debug behavior unchanged.
3. Preserve full regression stability.

## Technical Design
### Files
- `bot_agent/adaptive_runtime/routing_stage_helpers.py`
- `bot_agent/adaptive_runtime/runtime_misc_helpers.py`

### Changes
Renamed:
- `detect_fast_path_reason_fn` -> `detect_fast_path_reason`
- `truncate_preview_fn` -> `truncate_preview`

Updated all callsites accordingly.

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

