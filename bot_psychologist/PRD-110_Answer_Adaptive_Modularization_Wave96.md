# PRD-110: `answer_adaptive.py` Modularization (Wave 96)

## Context
Stage-4 passed `fallback_model_name` from facade even though caller always supplied `llm_model_name`.

## Scope (Wave 96)
Remove redundant `fallback_model_name` pass-through from facade/runtime Stage-4 contract.

## Objectives
1. Reduce Stage-4 facade argument surface.
2. Keep LLM metrics fallback semantics unchanged by binding fallback model to `llm_model_name` internally.
3. Validate with targeted and full suites.

## Technical Design
Update `bot_agent/adaptive_runtime/runtime_misc_helpers.py`:
- remove `_run_generation_and_success_stage(...)` arg `fallback_model_name`.
- pass `fallback_model_name=llm_model_name` into `_run_full_path_success_stage(...)`.

Update `bot_agent/answer_adaptive.py`:
- remove obsolete Stage-4 call arg `fallback_model_name=llm_model_name`.

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
