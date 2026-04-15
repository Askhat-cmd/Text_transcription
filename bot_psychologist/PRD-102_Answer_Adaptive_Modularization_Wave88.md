# PRD-102: `answer_adaptive.py` Modularization (Wave 88)

## Context
Fast-path stage still required multiple success/observability helper dependencies from `answer_adaptive.py`, even though these are runtime-internal helpers.

## Scope (Wave 88)
Narrow `_run_fast_path_stage(...)` by localizing success-response/observability helper wiring in `runtime_misc_helpers.py`.

## Objectives
1. Reduce fast-path facade call-surface in `answer_adaptive.py`.
2. Keep fast-path behavior and trace contracts unchanged.
3. Validate with expanded targeted and full suites.

## Technical Design
Update `bot_agent/adaptive_runtime/runtime_misc_helpers.py`:
- remove `_run_fast_path_stage(...)` params:
  - `build_fast_path_success_response_fn`
  - `build_success_response_fn`
  - `build_fast_success_metadata_fn`
  - `attach_success_observability_fn`
  - `strip_legacy_runtime_metadata_fn`
  - `attach_debug_payload_fn`
  - `finalize_success_debug_trace_fn`
  - `strip_legacy_trace_fields_fn`
- localize imports and pass direct runtime helpers:
  - from `response_utils`: `_build_fast_path_success_response`, `_build_success_response`, `_build_fast_success_metadata`, `_attach_success_observability`, `_attach_debug_payload`
  - from `trace_helpers`: `_strip_legacy_runtime_metadata`, `_finalize_success_debug_trace`, `_strip_legacy_trace_fields`

Update `bot_agent/answer_adaptive.py`:
- remove obsolete fast-path call args listed above.
- remove now-unused imports `_build_fast_success_metadata`, `_build_fast_path_success_response`.

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
