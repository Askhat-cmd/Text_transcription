# PRD-149: `answer_adaptive.py` Modularization (Wave 135)

## Context
`retrieval_stage_helpers.py` remained a large mixed file (~581 lines) with both reusable retrieval pipeline helpers and orchestration glue.

## Scope (Wave 135)
Extract retrieval pipeline helpers into:
- `adaptive_runtime/retrieval_pipeline_helpers.py`

Moved functions:
- `_prepare_hybrid_query_stage`
- `_retrieve_blocks_with_degraded_mode`
- `_dedupe_and_apply_progressive_rag`
- `_prepare_conditional_rerank`
- `_run_retrieval_and_rerank_stage`

Keep orchestration in:
- `adaptive_runtime/retrieval_stage_helpers.py` with `_run_retrieval_routing_context_stage` only.

## Objectives
1. Isolate reusable retrieval pipeline logic.
2. Reduce complexity of stage orchestration module.
3. Preserve behavior and contracts.

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
