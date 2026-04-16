# PRD-047: `answer_adaptive.py` Modularization (Wave 33)

## Context
The no-retrieval partial-response branch still had a large inline block with state update, persistence, and failure-trace finalization.

## Scope (Wave 33)
Extract no-retrieval partial-flow orchestration into response helper.

## Objectives
1. Reduce error/partial-flow complexity in `answer_adaptive.py`.
2. Preserve partial-response payload and trace-finalization contract.
3. Keep working-state and turn-persistence side effects unchanged.

## Technical Design
Extend `adaptive_runtime/response_utils.py (removed in Wave 142)` with:
- `_handle_no_retrieval_partial_response(...)`

Update `answer_adaptive.py`:
- replace inline no-retrieval branch with helper call and immediate return

## Test Plan
Targeted:
- `tests/integration/test_adaptive_stream_contract.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_pipeline_without_sd.py`
- `tests/regression/test_streaming_sd_runtime_disabled_contract.py`
- `tests/test_sse_payload.py`

Full:
- `pytest -q tests`


