# PRD-021: `answer_adaptive.py` Modularization (Wave 7)

## Context
`answer_adaptive.py` still contained duplicated construction of `status=success` API payloads in fast-path and full-path branches.

## Scope (Wave 7)
Centralize success payload composition in shared runtime helper:
- state analysis serialization
- top-level response envelope (`status/answer/state_analysis/.../metadata/timestamp/processing_time_seconds`)

## Objectives
1. Remove duplicated response-envelope logic.
2. Preserve API/SSE/trace contracts exactly.
3. Keep orchestration focused on data flow, not payload boilerplate.

## Technical Design
1. Extend `adaptive_runtime/response_utils.py` with:
   - `_serialize_state_analysis(...)`
   - `_build_success_response(...)`
2. Replace inline success payload dicts in both branches of `answer_adaptive.py` with helper calls.

## Tasks
1. Add reusable success payload helpers.
2. Integrate helper in fast-path branch.
3. Integrate helper in full-path branch.
4. Run targeted tests.
5. Run full suite.
6. Record results in Wave 7 tasklist.

## Test Plan
Targeted:
- `tests/integration/test_adaptive_stream_contract.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_pipeline_without_sd.py`
- `tests/regression/test_streaming_sd_runtime_disabled_contract.py`
- `tests/test_sse_payload.py`

Full:
- `pytest -q tests`
