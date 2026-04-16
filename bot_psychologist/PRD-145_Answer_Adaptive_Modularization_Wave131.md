# PRD-145: `answer_adaptive.py` Modularization (Wave 131)

## Context
`runtime_misc_helpers.py` remained a heavy mixed-responsibility module even after previous waves. It contained pricing, fast-path stage orchestration, and full-path stage orchestration in one file.

## Scope (Wave 131, accelerated batch)
Split `runtime_misc_helpers.py` into focused modules:

1. `adaptive_runtime/pricing_helpers.py`
- `COST_PER_1K_TOKENS`
- `_estimate_cost`

2. `adaptive_runtime/fast_path_stage_helpers.py`
- `_run_fast_path_stage`

3. `adaptive_runtime/full_path_stage_helpers.py`
- `_run_full_path_llm_stage`
- `_run_generation_and_success_stage`

4. Convert `adaptive_runtime/runtime_misc_helpers.py` into a thin compatibility facade re-exporting the same callable names.

## Objectives
1. Keep behavior/contract unchanged.
2. Reduce orchestration file size and increase maintainability.
3. Preserve existing import paths used by runtime/tests.

## Technical Design
### Files
- `bot_agent/adaptive_runtime/pricing_helpers.py` (new)
- `bot_agent/adaptive_runtime/fast_path_stage_helpers.py` (new)
- `bot_agent/adaptive_runtime/full_path_stage_helpers.py` (new)
- `bot_agent/adaptive_runtime/runtime_misc_helpers.py` (rewritten as compatibility layer)

### Contract
- External callers still import from `runtime_misc_helpers` safely.
- Runtime call graph stays equivalent; only code location changes.

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
