# PRD-091: `answer_adaptive.py` Modularization (Wave 77)

## Context
Stage-3 call still injected hybrid-query builder dependencies (`recent_user_turns_fn`, `hybrid_query_builder_cls`) from `answer_adaptive.py`, although hybrid query assembly is retrieval-internal behavior.

## Scope (Wave 77)
Localize hybrid-query assembly dependencies inside retrieval runtime helper.

## Objectives
1. Reduce Stage-3 helper call surface by two parameters.
2. Preserve hybrid query generation behavior.
3. Validate with expanded targeted and full test suites.

## Technical Design
Update `bot_agent/adaptive_runtime/retrieval_stage_helpers.py`:
- in `_prepare_hybrid_query_stage(...)`:
  - remove params `recent_user_turns_fn`, `hybrid_query_builder_cls`
  - use local imports:
    - `HybridQueryBuilder` from retrieval
    - `_recent_user_turns` from trace helpers
- remove these params from `_run_retrieval_routing_context_stage(...)` and its call into `_prepare_hybrid_query_stage(...)`.

Update `bot_agent/answer_adaptive.py`:
- remove now-unused imports `HybridQueryBuilder` and `_recent_user_turns`.
- remove obsolete Stage-3 arguments.

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
