# PRD-076: `answer_adaptive.py` Modularization (Wave 62)

## Context
After Wave 61, retrieval pre-stage still built `hybrid_query` inline inside `answer_question_adaptive(...)`.

## Scope (Wave 62)
Extract hybrid-query preparation block into retrieval runtime helpers and keep orchestration call-site compact.

## Objectives
1. Reduce Stage-3 inline complexity in `answer_question_adaptive(...)`.
2. Keep retrieval query semantics unchanged.
3. Preserve full runtime/test behavior.

## Technical Design
Update `adaptive_runtime/retrieval_stage_helpers.py`:
- add `_prepare_hybrid_query_stage(...)` that composes:
  - retrieval working-state construction
  - recent user turns selection
  - `HybridQueryBuilder` invocation
  - retrieval pre-stage logging

Update `answer_adaptive.py`:
- import `_prepare_hybrid_query_stage` as runtime helper.
- replace inline `hybrid_query` assembly block with helper call.

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
