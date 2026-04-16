# PRD-036: `answer_adaptive.py` Modularization (Wave 22)

## Context
Failure branches (`partial`, `LLM error`, outer exception) repeated trace-finalization logic: chunk lists, memory snapshot, cost estimate, payload finalize.

## Scope (Wave 22)
Extract shared failure-trace finalization helper and reuse across all failure branches.

## Objectives
1. Remove duplicated failure trace finalization code.
2. Keep debug-trace contract unchanged for each failure path.
3. Preserve per-branch specifics (skipped stages, total-duration flag, legacy-strip behavior).

## Technical Design
Add helper in `adaptive_runtime/trace_helpers.py`:
- `_finalize_failure_debug_trace(...)`

Update `answer_adaptive.py`:
- use helper in `partial` path (`blocks_after_cap=0`, skipped stages)
- use helper in `LLM error` path
- use helper in outer exception path (`include_chunks=False`, `include_total_duration=False`, legacy strip)

## Test Plan
Targeted:
- `tests/integration/test_adaptive_stream_contract.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_pipeline_without_sd.py`
- `tests/regression/test_streaming_sd_runtime_disabled_contract.py`
- `tests/test_sse_payload.py`

Full:
- `pytest -q tests`
