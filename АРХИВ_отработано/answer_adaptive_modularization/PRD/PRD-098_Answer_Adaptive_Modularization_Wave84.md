# PRD-098: `answer_adaptive.py` Modularization (Wave 84)

## Context
Fast-path Stage still received many internal LLM-cycle DI parameters from `answer_adaptive.py`. These internals are stable runtime helpers and can be localized in `runtime_misc_helpers.py`.

## Scope (Wave 84)
Narrow `_run_fast_path_stage(...)` contract by localizing internal LLM-cycle helper dependencies.

## Objectives
1. Reduce fast-path call surface in `answer_adaptive.py`.
2. Preserve fast-path behavior, test monkeypatch compatibility, and trace contracts.
3. Validate with expanded targeted and full suites.

## Technical Design
Update `bot_agent/adaptive_runtime/runtime_misc_helpers.py`:
- remove `_run_fast_path_stage(...)` DI params:
  - `run_llm_generation_cycle_fn`
  - `build_prompt_stack_override_fn`
  - `prepare_llm_prompt_previews_fn`
  - `generate_llm_with_trace_fn`
  - `build_llm_call_trace_fn`
  - `format_and_validate_llm_answer_fn`
  - `run_validation_retry_generation_fn`
  - `apply_output_validation_observability_fn`
- keep class DI (`response_generator_cls`, `response_formatter_cls`) for monkeypatch-compatible tests.
- localize internal calls:
  - `_run_llm_generation_cycle`, `_build_prompt_stack_override`, `_generate_llm_with_trace`, `_format_and_validate_llm_answer`, `_run_validation_retry_generation`
  - trace helpers for prompt previews, call trace and validation observability.

Update `bot_agent/answer_adaptive.py`:
- remove obsolete fast-path call args listed above.
- remove now-unused imports that were only needed by those args.

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
