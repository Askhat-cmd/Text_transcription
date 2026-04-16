# PRD-041: `answer_adaptive.py` Modularization (Wave 27)

## Context
Retrieval bootstrap logic (retriever init, degraded fallback, author intent, blend/single execution) remained as a large inline block inside Stage 3.

## Scope (Wave 27)
Extract retrieval bootstrap/execution into dedicated retrieval-stage helper module.

## Objectives
1. Reduce Stage 3 orchestration complexity.
2. Preserve degraded mode behavior and logs.
3. Preserve author-intent and blend/single retrieval contract.

## Technical Design
Add module `adaptive_runtime/retrieval_stage_helpers.py` with:
- `_retrieve_blocks_with_degraded_mode(...)`

Update `answer_adaptive.py`:
- replace inline retrieval bootstrap block with helper call
- keep stage append/degraded trace behavior intact

## Test Plan
Targeted:
- `tests/integration/test_adaptive_stream_contract.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_pipeline_without_sd.py`
- `tests/regression/test_streaming_sd_runtime_disabled_contract.py`
- `tests/test_sse_payload.py`

Full:
- `pytest -q tests`
