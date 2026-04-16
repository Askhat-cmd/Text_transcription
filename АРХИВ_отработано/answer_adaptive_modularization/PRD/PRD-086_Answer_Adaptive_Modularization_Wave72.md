# PRD-086: `answer_adaptive.py` Modularization (Wave 72)

## Context
`adaptive_runtime/trace_helpers.py` still had one internal function-injection (`build_retrieval_detail_fn`) inside `_build_retrieval_debug_details(...)`, although both helpers are local to the same module.

## Scope (Wave 72)
Remove the last internal retrieval-detail function injection in trace debug assembly.

## Objectives
1. Further simplify local helper contracts.
2. Preserve trace payload structure and values.
3. Validate no regressions in targeted and full suites.

## Technical Design
Update `bot_agent/adaptive_runtime/trace_helpers.py`:
- in `_build_retrieval_debug_details(...)`:
  - remove arg `build_retrieval_detail_fn`
  - call `_build_retrieval_detail(...)` directly for all sections
- in `_attach_retrieval_observability(...)`:
  - stop passing `build_retrieval_detail_fn` argument

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
