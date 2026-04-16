# PRD-113: `answer_adaptive.py` Modularization (Wave 99)

## Context
Fast-path Stage-2 still received two runtime-stable callbacks from facade:
- context refresh + trace snapshot apply
- fast-path block builder

## Scope (Wave 99)
Localize these callbacks in `runtime_misc_helpers.py` and remove obsolete pass-through args from `answer_adaptive.py`.

## Objectives
1. Continue narrowing fast-path facade contract.
2. Keep test harness compatibility and runtime behavior unchanged.
3. Validate on expanded targeted and full suites.

## Technical Design
Update `bot_agent/adaptive_runtime/runtime_misc_helpers.py`:
- remove `_run_fast_path_stage(...)` args:
  - `refresh_context_and_apply_trace_snapshot_fn`
  - `build_fast_path_block_fn`
- localize imports:
  - `_refresh_context_and_apply_trace_snapshot`
  - `_build_fast_path_block`
- wire localized callables in fast-path Stage-2 flow.

Update `bot_agent/answer_adaptive.py`:
- remove obsolete fast-path call args listed above.
- remove now-unused facade imports tied to removed pass-throughs.

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
