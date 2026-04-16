# PRD-073: `answer_adaptive.py` Modularization (Wave 59)

## Context
After Wave 58, `answer_adaptive.py` still had a broad facade layer of thin `**kwargs` wrappers that only proxied calls to runtime helpers.

## Scope (Wave 59)
Remove the remaining thin `**kwargs` wrappers and switch call sites to direct `_runtime_*` helper usage.

## Objectives
1. Reduce indirection in main pipeline code.
2. Keep all runtime contracts and behavior unchanged.
3. Prepare cleaner surface for next extraction waves.

## Technical Design
Update `answer_adaptive.py`:
- remove thin wrappers:
  - `_generate_llm_with_trace`, `_run_validation_retry_generation`, `_collect_llm_session_metrics`, `_build_prompt_stack_override`, `_run_llm_generation_cycle`, `_format_and_validate_llm_answer`, `_run_full_path_llm_stage`, `_run_fast_path_stage`, `_dedupe_and_apply_progressive_rag`, `_prepare_conditional_rerank`, `_run_retrieval_and_rerank_stage`, `_run_state_and_pre_routing_pipeline`, `_resolve_routing_and_apply_block_cap`, `_finalize_routing_context_and_trace`, `_build_path_recommendation_if_enabled`, `_build_fast_path_success_response`, `_build_full_path_success_response`, `_build_unhandled_exception_response`, `_run_full_path_success_stage`, `_run_no_retrieval_stage`, `_handle_llm_generation_error_response`, `_prepare_adapted_blocks_and_attach_observability`, `_compose_state_context`, `_refresh_context_and_apply_trace_snapshot`, `_apply_output_validation_observability`.
- replace all in-file call sites with direct `_runtime_*` references.

## Test Plan
Targeted:
- `tests/test_retrieval_pipeline_simplified.py`
- `tests/integration/test_degraded_mode_without_retrieval.py`
- `tests/e2e/test_degraded_retrieval_case.py`
- `tests/integration/test_sparse_output_triggers_regeneration_hint.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_routing_recalibration_for_exploratory_queries.py`
- `tests/integration/test_adaptive_stream_contract.py`
- `tests/test_sse_payload.py`

Full:
- `pytest -q tests --maxfail=1`
