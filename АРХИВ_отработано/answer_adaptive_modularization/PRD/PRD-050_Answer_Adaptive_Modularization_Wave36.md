# PRD-050: `answer_adaptive.py` Modularization (Wave 36)

## Context
Both fast-path and full-path branches duplicated the same runtime-memory refresh block: snapshot refresh, trace snapshot attach, context-mode assignment, and context build logging.

## Scope (Wave 36)
Extract duplicated runtime context-refresh + trace wiring into a single helper in `adaptive_runtime/trace_helpers.py`.

## Objectives
1. Remove duplicated snapshot/context trace logic from orchestrator.
2. Keep `snapshot_v11/snapshot_v12` and `context_mode` trace fields unchanged.
3. Preserve conversation-context refresh behavior for both fast and full paths.

## Technical Design
Add helper in `adaptive_runtime/trace_helpers.py`:
- `_refresh_context_and_apply_trace_snapshot(...)`

Update `answer_adaptive.py`:
- replace duplicated inline blocks (fast-path and full-path) with helper call.

## Test Plan
Targeted:
- `tests/integration/test_adaptive_stream_contract.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_pipeline_without_sd.py`
- `tests/regression/test_streaming_sd_runtime_disabled_contract.py`
- `tests/test_sse_payload.py`

Full:
- `pytest -q tests --maxfail=1`
