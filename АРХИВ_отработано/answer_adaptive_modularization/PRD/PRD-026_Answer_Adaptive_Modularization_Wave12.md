# PRD-026: `answer_adaptive.py` Modularization (Wave 12)

## Context
Stage 3 retrieval debug payload assembly still contained a large inline block in `answer_adaptive.py`.

## Scope (Wave 12)
Extract retrieval debug details builder to shared trace helpers and replace inline construction.

## Objectives
1. Reduce Stage 3 inline complexity.
2. Preserve debug payload schema and values.
3. Keep test contracts green.

## Technical Design
Add helper in `adaptive_runtime/trace_helpers.py`:
- `_build_retrieval_debug_details(...)`

Use helper in `answer_adaptive.py` for `debug_info["retrieval_details"]`.

## Test Plan
Targeted:
- `tests/integration/test_adaptive_stream_contract.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_pipeline_without_sd.py`
- `tests/regression/test_streaming_sd_runtime_disabled_contract.py`
- `tests/test_sse_payload.py`

Full:
- `pytest -q tests`
