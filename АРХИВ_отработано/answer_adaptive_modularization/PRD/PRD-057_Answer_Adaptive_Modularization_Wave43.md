# PRD-057: `answer_adaptive.py` Modularization (Wave 43)

## Context
The terminal `except Exception` branch in `answer_adaptive.py` still embedded error response construction, memory persistence fallback, and failure trace finalization.

## Scope (Wave 43)
Extract terminal unhandled-exception response flow into response runtime helper.

## Objectives
1. Reduce orchestrator complexity in global error path.
2. Preserve error payload and failure trace contract.
3. Keep best-effort persistence behavior unchanged.

## Technical Design
Add helper in `adaptive_runtime/response_utils.py (removed in Wave 142)`:
- `_build_unhandled_exception_response(...)`

Update `answer_adaptive.py`:
- replace inline `except Exception` response block with helper call.

## Test Plan
Targeted:
- `tests/integration/test_adaptive_stream_contract.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_pipeline_without_sd.py`
- `tests/regression/test_streaming_sd_runtime_disabled_contract.py`
- `tests/test_sse_payload.py`

Full:
- `pytest -q tests --maxfail=1`

