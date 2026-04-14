# PRD-045: `answer_adaptive.py` Modularization (Wave 31)

## Context
Stage 3 full-path flow still had a large inline block that populated routing/retrieval debug-trace fields.

## Scope (Wave 31)
Extract routing-stage debug-trace payload construction into routing helper.

## Objectives
1. Reduce orchestration noise in `answer_adaptive.py`.
2. Preserve all routing debug keys and value semantics.
3. Keep trace contract stable for Web UI and diagnostics.

## Technical Design
Extend `adaptive_runtime/routing_stage_helpers.py` with:
- `_attach_routing_stage_debug_trace(...)`

Update `answer_adaptive.py`:
- replace inline `debug_trace[...]` assignment block with helper call
- keep downstream snapshot/context/LLM trace assembly unchanged

## Test Plan
Targeted:
- `tests/integration/test_adaptive_stream_contract.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_pipeline_without_sd.py`
- `tests/regression/test_streaming_sd_runtime_disabled_contract.py`
- `tests/test_sse_payload.py`

Full:
- `pytest -q tests`

