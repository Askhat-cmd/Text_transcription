# PRD-020: `answer_adaptive.py` Modularization (Wave 6)

## Context
After Wave 5, `answer_adaptive.py` still had duplicated debug-trace enrichment logic in two main runtime branches (fast-path and full retrieval path).

## Scope (Wave 6)
Extract and centralize repeated trace enrichment logic to `adaptive_runtime/trace_helpers.py`:
- model info injection (`primary/classifier/embedding/reranker`)
- token/session metrics injection (with optional fallback aggregation from `llm_calls`)

## Objectives
1. Reduce duplication in the monolith orchestration.
2. Keep trace contract and SSE behavior unchanged.
3. Preserve runtime observability fields expected by Web UI trace panels.

## Technical Design
1. Add helper functions in `bot_agent/adaptive_runtime/trace_helpers.py`:
   - `_apply_trace_model_info(debug_trace)`
   - `_apply_trace_token_metrics(debug_trace, ..., aggregate_from_llm_calls=False)`
2. Replace duplicated inline blocks in `answer_adaptive.py` with helper calls.

## Tasks
1. Add new trace helper functions.
2. Wire helper usage in fast-path trace finalization.
3. Wire helper usage in full-path trace finalization.
4. Run targeted integration/regression tests.
5. Run full test suite.
6. Update Wave 6 tasklist snapshot.

## Test Plan
Targeted:
- `tests/integration/test_adaptive_stream_contract.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_pipeline_without_sd.py`
- `tests/regression/test_streaming_sd_runtime_disabled_contract.py`
- `tests/test_sse_payload.py`

Full:
- `pytest -q tests`
