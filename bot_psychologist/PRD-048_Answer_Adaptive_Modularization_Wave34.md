# PRD-048: `answer_adaptive.py` Modularization (Wave 34)

## Context
Post-retrieval observability assembly (debug_info + debug_trace chunk lists) remained inline in Stage 3 full-path flow.

## Scope (Wave 34)
Extract post-retrieval observability payload assembly into trace helper.

## Objectives
1. Reduce inline observability mapping in `answer_adaptive.py`.
2. Preserve debug payload keys consumed by trace/UI.
3. Keep retrieval/rerank/routing diagnostics contract unchanged.

## Technical Design
Extend `adaptive_runtime/trace_helpers.py` with:
- `_attach_retrieval_observability(...)`

Update `answer_adaptive.py`:
- replace inline debug-info/debug-trace post-retrieval block with helper call

## Test Plan
Targeted:
- `tests/integration/test_adaptive_stream_contract.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_pipeline_without_sd.py`
- `tests/regression/test_streaming_sd_runtime_disabled_contract.py`
- `tests/test_sse_payload.py`

Full:
- `pytest -q tests`

