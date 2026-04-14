# PRD-051: `answer_adaptive.py` Modularization (Wave 37)

## Context
LLM error handling after generation remained inline in `answer_adaptive.py` and mixed response construction, persistence, and trace-finalization concerns inside the main orchestration function.

## Scope (Wave 37)
Extract LLM generation error branch into response runtime helper.

## Objectives
1. Reduce orchestrator size by removing inline LLM error branch.
2. Preserve error response payload and debug-trace finalization contract.
3. Keep best-effort turn persistence behavior unchanged.

## Technical Design
Add helper in `adaptive_runtime/response_utils.py`:
- `_handle_llm_generation_error_response(...)`

Update `answer_adaptive.py`:
- replace inline `if llm_result.get("error") ...` branch with helper call.

## Test Plan
Targeted:
- `tests/integration/test_adaptive_stream_contract.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_pipeline_without_sd.py`
- `tests/regression/test_streaming_sd_runtime_disabled_contract.py`
- `tests/test_sse_payload.py`

Full:
- `pytest -q tests --maxfail=1`
