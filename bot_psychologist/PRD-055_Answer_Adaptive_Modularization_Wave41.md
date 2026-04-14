# PRD-055: `answer_adaptive.py` Modularization (Wave 41)

## Context
Fast-path success finalization remained large inline logic in orchestrator: session token metrics, persistence, success payload assembly, debug routing payload, and trace finalization wiring.

## Scope (Wave 41)
Extract fast-path success finalization into response runtime helper.

## Objectives
1. Reduce orchestrator complexity in fast-path return branch.
2. Preserve response contract and debug-trace contract for fast-path.
3. Keep token/cost aggregation and metadata unchanged.

## Technical Design
Add helper in `adaptive_runtime/response_utils.py`:
- `_build_fast_path_success_response(...)`

Update `answer_adaptive.py`:
- replace large inline fast-path finalize block with helper call.

## Test Plan
Targeted:
- `tests/integration/test_adaptive_stream_contract.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_pipeline_without_sd.py`
- `tests/regression/test_streaming_sd_runtime_disabled_contract.py`
- `tests/test_sse_payload.py`

Full:
- `pytest -q tests --maxfail=1`
