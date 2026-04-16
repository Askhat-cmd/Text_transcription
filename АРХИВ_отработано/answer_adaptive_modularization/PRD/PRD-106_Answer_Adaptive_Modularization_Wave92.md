# PRD-106: `answer_adaptive.py` Modularization (Wave 92)

## Context
Stage-4 success bridge still passed `build_sources/log_blocks` callbacks from facade to runtime helper.

## Scope (Wave 92)
Localize source-building and block-logging wiring inside `runtime_misc_helpers.py`.

## Objectives
1. Reduce Stage-4 DI surface in `answer_adaptive.py`.
2. Keep success payload and trace observability unchanged.
3. Validate with expanded targeted and full suites.

## Technical Design
Update `bot_agent/adaptive_runtime/runtime_misc_helpers.py`:
- narrow `_run_generation_and_success_stage(...)` signature by removing:
  - `build_sources_from_blocks_fn`
  - `log_blocks_fn`
- localize imports and pass-through wiring:
  - `_build_sources_from_blocks` from `response_utils`
  - `_log_blocks` from `trace_helpers`
- keep call contract for `_run_full_path_success_stage(...)` unchanged.

Update `bot_agent/answer_adaptive.py`:
- remove obsolete Stage-4 call args.
- remove now-unused imports `_build_sources_from_blocks` and `_log_blocks`.

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
