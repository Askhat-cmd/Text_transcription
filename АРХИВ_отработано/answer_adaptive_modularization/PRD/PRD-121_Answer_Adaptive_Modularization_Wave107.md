# PRD-121: `answer_adaptive.py` Modularization (Wave 107)

## Context
After Stage contract naming cleanup, `answer_adaptive.py` still contained stale compatibility imports and one dead wrapper not used by facade/runtime/tests.

## Scope (Wave 107)
Perform dead-code cleanup in facade module only:
- remove stale imports that are no longer consumed by `answer_adaptive.py`
- remove unused wrapper `_fallback_sd_result(...)`

## Objectives
1. Keep facade surface minimal and readable.
2. Reduce drift between facade imports and real runtime usage.
3. Preserve all runtime behavior and external contracts used by tests.

## Technical Design
Update `bot_agent/answer_adaptive.py`:
- remove unused imports:
  - `_build_partial_response`
  - `_extract_block_trace_fields`
  - `_build_chunk_trace_item`
  - `_runtime_fallback_sd_result`
- remove dead function:
  - `_fallback_sd_result(...)`

No behavior changes in pipeline execution.

## Test Plan
Targeted:
- `tests/integration/test_generation_validation_separation.py`
- `tests/integration/test_sparse_output_triggers_regeneration_hint.py`
- `tests/unit/test_query_is_passed_to_output_validation_policy_v1031.py`
- `tests/unit/test_sd_runtime_disabled.py`
- `tests/test_retrieval_pipeline_simplified.py`
- `tests/unit/test_curious_not_auto_informational.py`
- `tests/unit/test_user_level_adapter_removed.py`
- `tests/unit/test_sd_legacy_final_cleanup_prompt_context.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_degraded_mode_without_retrieval.py`

Full:
- `pytest -q`
