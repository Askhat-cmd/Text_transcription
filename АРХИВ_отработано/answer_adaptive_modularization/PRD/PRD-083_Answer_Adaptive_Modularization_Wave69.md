# PRD-083: `answer_adaptive.py` Modularization (Wave 69)

## Context
After Wave 68, Stage-3 retrieval orchestration still accepted several function-injection parameters that are local implementation details of `adaptive_runtime/retrieval_stage_helpers.py`.

## Scope (Wave 69)
Shrink Stage-3 helper contracts by removing internal function-injection parameters and using module-local helper calls directly.

## Objectives
1. Reduce parameter noise in Stage-3 orchestration APIs.
2. Keep runtime behavior unchanged.
3. Preserve all existing test contracts.

## Technical Design
Update `bot_agent/adaptive_runtime/retrieval_stage_helpers.py`:
- in `_run_retrieval_and_rerank_stage(...)`:
  - remove params `dedupe_and_apply_progressive_rag_fn`, `prepare_conditional_rerank_fn`
  - call `_dedupe_and_apply_progressive_rag(...)` and `_prepare_conditional_rerank(...)` directly
- in `_run_retrieval_routing_context_stage(...)`:
  - remove params `prepare_hybrid_query_stage_fn`, `dedupe_and_apply_progressive_rag_fn`, `prepare_conditional_rerank_fn`, `informational_branch_enabled_fn`
  - add plain bool param `informational_branch_enabled`
  - call `_prepare_hybrid_query_stage(...)` directly
  - pass `lambda: informational_branch_enabled` only at boundary that still expects callable

Update `bot_agent/answer_adaptive.py`:
- simplify Stage-3 call to `_runtime_run_retrieval_routing_context_stage(...)`
- remove now-unused imports from `adaptive_runtime.retrieval_stage_helpers`

## Test Plan
Expanded targeted:
- `tests/regression/test_no_level_based_prompting.py`
- `tests/test_retrieval_pipeline_simplified.py`
- `tests/integration/test_degraded_mode_without_retrieval.py`
- `tests/e2e/test_degraded_retrieval_case.py`
- `tests/integration/test_sparse_output_triggers_regeneration_hint.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_routing_recalibration_for_exploratory_queries.py`
- `tests/integration/test_adaptive_stream_contract.py`
- `tests/test_sse_payload.py`
- `tests/unit/test_curious_not_auto_informational.py`
- `tests/unit/test_user_level_adapter_removed.py`
- `tests/unit/test_sd_legacy_final_cleanup_prompt_context.py`
- `tests/unit/test_query_is_passed_to_output_validation_policy_v1031.py`
- `tests/integration/test_generation_validation_separation.py`

Full:
- `pytest -q tests --maxfail=1`
