# PRD-043: `answer_adaptive.py` Modularization (Wave 29)

## Context
Conditional rerank preparation (mode/confidence/flags/should_run/k) remained as inline logic in Stage 3.

## Scope (Wave 29)
Extract rerank-preparation decision logic into retrieval-stage helper while keeping rerank execution in orchestrator.

## Objectives
1. Reduce Stage 3 inline branch density.
2. Preserve rerank gate contract and decision inputs.
3. Keep runtime behavior and trace fields unchanged.

## Technical Design
Extend `adaptive_runtime/retrieval_stage_helpers.py` with:
- `_prepare_conditional_rerank(...)`

Update `answer_adaptive.py`:
- replace inline rerank decision-prep block with helper call
- keep actual rerank execution path unchanged

## Test Plan
Targeted:
- `tests/integration/test_adaptive_stream_contract.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_pipeline_without_sd.py`
- `tests/regression/test_streaming_sd_runtime_disabled_contract.py`
- `tests/test_sse_payload.py`

Full:
- `pytest -q tests`
