# PRD-078: `answer_adaptive.py` Modularization (Wave 64)

## Context
Stage-3 orchestration in `answer_question_adaptive(...)` remained dense even after earlier helper extraction, combining retrieval, routing cap, routing context finalization, no-retrieval early-return handling, and retrieval observability assembly in one inline block.

## Scope (Wave 64)
Extract Stage-3 orchestration into a dedicated retrieval runtime helper.

## Objectives
1. Significantly reduce Stage-3 inline complexity in `answer_adaptive.py`.
2. Preserve no-retrieval branch behavior and debug/trace contracts.
3. Keep all runtime outputs unchanged under full regression suite.

## Technical Design
Update `adaptive_runtime/retrieval_stage_helpers.py`:
- add `_run_retrieval_routing_context_stage(...)` high-level orchestrator that composes:
  - `_prepare_hybrid_query_stage(...)`
  - `_run_retrieval_and_rerank_stage(...)`
  - routing cap resolution
  - routing context finalization
  - no-retrieval early response branch
  - retrieval observability/adapted blocks preparation

Update `answer_adaptive.py`:
- import and use `_run_retrieval_routing_context_stage(...)`.
- replace long inline Stage-3 sequence with one helper call + compact unpacking.

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
