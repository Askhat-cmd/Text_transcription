# PRD-040: `answer_adaptive.py` Modularization (Wave 26)

## Context
Fast-path and full-path success branches duplicated post-processing of successful result payload (metadata sanitization, debug attach, trace finalization).

## Scope (Wave 26)
Extract shared success observability helper and reuse it in both success branches.

## Objectives
1. Remove duplicated success payload post-processing code.
2. Preserve metadata/debug/debug_trace contracts.
3. Keep branch-specific trace aggregation modes (`aggregate_from_llm_calls`) configurable.

## Technical Design
Add helper in `adaptive_runtime/response_utils.py`:
- `_attach_success_observability(...)`

Update `answer_adaptive.py`:
- replace fast-path success post-processing block
- replace full-path success post-processing block

## Test Plan
Targeted:
- `tests/integration/test_adaptive_stream_contract.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_pipeline_without_sd.py`
- `tests/regression/test_streaming_sd_runtime_disabled_contract.py`
- `tests/test_sse_payload.py`

Full:
- `pytest -q tests`
