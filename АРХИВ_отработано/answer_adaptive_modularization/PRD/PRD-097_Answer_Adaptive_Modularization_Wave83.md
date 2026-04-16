# PRD-097: `answer_adaptive.py` Modularization (Wave 83)

## Context
After Wave 82, Stage-4 still passed a large group of LLM-cycle internals into `runtime_misc_helpers` even though these internals are stable and can be resolved locally.

## Scope (Wave 83)
Localize full-path LLM-cycle helper dependencies inside `runtime_misc_helpers.py` and reduce Stage-4 call surface in `answer_adaptive.py`.

## Objectives
1. Shrink Stage-4 argument contract without behavioral changes.
2. Keep full-path generation, validation retry, and error fallback behavior identical.
3. Validate on expanded targeted and full suites.

## Technical Design
Update `bot_agent/adaptive_runtime/runtime_misc_helpers.py`:
- Narrow `_run_full_path_llm_stage(...)` by removing DI params:
  - `run_llm_generation_cycle_fn`
  - `response_generator_cls`
  - `build_prompt_stack_override_fn`
  - `prepare_llm_prompt_previews_fn`
  - `generate_llm_with_trace_fn`
  - `build_llm_call_trace_fn`
  - `format_and_validate_llm_answer_fn`
  - `response_formatter_cls`
  - `run_validation_retry_generation_fn`
  - `apply_output_validation_observability_fn`
  - `handle_llm_generation_error_response_fn`
- Use localized internals/imports instead:
  - `_run_llm_generation_cycle`, `_build_prompt_stack_override`, `_generate_llm_with_trace`, `_format_and_validate_llm_answer`, `_run_validation_retry_generation`
  - trace helpers for prompt preview, llm-call trace, and output-validation observability
  - response helpers for generation error response
  - response classes `ResponseGenerator`, `ResponseFormatter`
- Narrow `_run_generation_and_success_stage(...)` accordingly.

Update `bot_agent/answer_adaptive.py`:
- Remove obsolete Stage-4 args that are now localized inside runtime helpers.
- Remove now-unused import `_runtime_handle_llm_generation_error_response`.

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
