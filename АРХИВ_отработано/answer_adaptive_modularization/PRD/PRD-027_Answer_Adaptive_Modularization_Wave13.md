# PRD-027: `answer_adaptive.py` Modularization (Wave 13)

## Context
Success-path debug payload assembly still repeated memory/time/token assignments across branches.

## Scope (Wave 13)
Extract common success debug payload and success trace finalization helpers.

## Objectives
1. Reduce repeated success debug code.
2. Keep trace and metadata contracts unchanged.
3. Preserve branch-specific legacy-strip behavior.

## Technical Design
Add helpers:
- `response_utils._attach_debug_payload(...)`
- `trace_helpers._finalize_success_debug_trace(...)`

Integrate in fast-path and full success branches in `answer_adaptive.py`.

## Test Plan
Targeted:
- `tests/integration/test_adaptive_stream_contract.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_pipeline_without_sd.py`
- `tests/regression/test_streaming_sd_runtime_disabled_contract.py`
- `tests/test_sse_payload.py`

Full:
- `pytest -q tests`
