# PRD-035: `answer_adaptive.py` Modularization (Wave 21)

## Context
Validation retry generation (`[VALIDATION_HINT]`) was duplicated in fast-path and full-path branches.

## Scope (Wave 21)
Extract shared validation-retry generation helper and reuse it in both branches.

## Objectives
1. Remove duplicated retry LLM call code.
2. Keep output-validation contract unchanged.
3. Preserve formatted retry answer behavior per route/mode.

## Technical Design
Add helper in `adaptive_runtime/runtime_misc_helpers.py`:
- `_run_validation_retry_generation(...)`

Update `answer_adaptive.py` retry callbacks to call the helper with branch-specific formatter lambda.

## Test Plan
Targeted:
- `tests/integration/test_adaptive_stream_contract.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_pipeline_without_sd.py`
- `tests/regression/test_streaming_sd_runtime_disabled_contract.py`
- `tests/test_sse_payload.py`

Full:
- `pytest -q tests`
