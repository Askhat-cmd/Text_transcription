# PRD-029: `answer_adaptive.py` Modularization (Wave 15)

## Context
Stage 3 still had inline logic for progressive feedback boosting and debug payload assembly for rerank/routing diagnostics.

## Scope (Wave 15)
Extract these blocks into shared trace helpers:
- progressive feedback block collection
- voyage rerank debug payload
- routing debug payload

## Objectives
1. Reduce Stage 3 orchestration noise.
2. Keep debug contracts and values unchanged.
3. Preserve regression behavior.

## Technical Design
Add in `adaptive_runtime/trace_helpers.py`:
- `_collect_progressive_feedback_blocks(...)`
- `_build_voyage_rerank_debug_payload(...)`
- `_build_routing_debug_payload(...)`

Replace inline code in `answer_adaptive.py` with helper calls.

## Test Plan
Targeted:
- `tests/integration/test_adaptive_stream_contract.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_pipeline_without_sd.py`
- `tests/regression/test_streaming_sd_runtime_disabled_contract.py`
- `tests/test_sse_payload.py`

Full:
- `pytest -q tests`
