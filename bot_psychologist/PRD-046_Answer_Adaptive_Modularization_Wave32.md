# PRD-046: `answer_adaptive.py` Modularization (Wave 32)

## Context
Path recommendation generation (Stage 6) remained as a large inline guarded block in `answer_adaptive.py`.

## Scope (Wave 32)
Extract path-recommendation gate and payload assembly into response helper.

## Objectives
1. Reduce inline orchestration code and try/except nesting.
2. Preserve path recommendation eligibility rules and payload structure.
3. Keep behavior unchanged when path recommendation is disabled or blocked by route.

## Technical Design
Extend `adaptive_runtime/response_utils.py` with:
- `_build_path_recommendation_if_enabled(...)`

Update `answer_adaptive.py`:
- replace inline Stage 6 path builder block with helper call

## Test Plan
Targeted:
- `tests/integration/test_adaptive_stream_contract.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_pipeline_without_sd.py`
- `tests/regression/test_streaming_sd_runtime_disabled_contract.py`
- `tests/test_sse_payload.py`

Full:
- `pytest -q tests`

