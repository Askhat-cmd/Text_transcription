# PRD-042: `answer_adaptive.py` Modularization (Wave 28)

## Context
Post-retrieval inline processing still contained deduplication and progressive-RAG reweighting with trace flags in Stage 3.

## Scope (Wave 28)
Extract dedupe + progressive rerank-by-weights into retrieval-stage helper and reuse in orchestration.

## Objectives
1. Reduce Stage 3 inline complexity.
2. Preserve retrieval dedupe logging and counts.
3. Preserve progressive-RAG trace flags (`progressive_rag_enabled`, `progressive_rag_error`).

## Technical Design
Extend `adaptive_runtime/retrieval_stage_helpers.py` with:
- `_dedupe_and_apply_progressive_rag(...)`

Update `answer_adaptive.py`:
- replace inline dedupe/rerank-by-weights block with helper call

## Test Plan
Targeted:
- `tests/integration/test_adaptive_stream_contract.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_pipeline_without_sd.py`
- `tests/regression/test_streaming_sd_runtime_disabled_contract.py`
- `tests/test_sse_payload.py`

Full:
- `pytest -q tests`
