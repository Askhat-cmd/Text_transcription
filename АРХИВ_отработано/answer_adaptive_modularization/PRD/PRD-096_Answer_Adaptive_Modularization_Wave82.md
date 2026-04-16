# PRD-096: `answer_adaptive.py` Modularization (Wave 82)

## Context
Stage-4 orchestration still passed two no-longer-needed callable dependencies into `_run_generation_and_success_stage(...)`, although both are now stable runtime internals.

## Scope (Wave 82)
Narrow Stage-4 contract by localizing direct calls inside `runtime_misc_helpers.py`.

## Objectives
1. Reduce call-surface noise in `answer_adaptive.py` Stage-4 invocation.
2. Keep full LLM/success path behavior unchanged.
3. Validate with expanded targeted and full suites.

## Technical Design
Update `bot_agent/adaptive_runtime/runtime_misc_helpers.py`:
- remove function params from `_run_generation_and_success_stage(...)`:
  - `run_full_path_llm_stage_fn`
  - `run_full_path_success_stage_fn`
- call internal `_run_full_path_llm_stage(...)` directly.
- local-import and call `_run_full_path_success_stage(...)` from `response_utils` directly.

Update `bot_agent/answer_adaptive.py`:
- remove obsolete Stage-4 args:
  - `run_full_path_llm_stage_fn=_runtime_run_full_path_llm_stage`
  - `run_full_path_success_stage_fn=_runtime_run_full_path_success_stage`
- remove now-unused imports for these symbols.

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
