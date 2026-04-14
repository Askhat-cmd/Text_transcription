# PRD-052: `answer_adaptive.py` Modularization (Wave 38)

## Context
Output-validation post-processing was duplicated between fast-path and full-path branches: retry LLM call capture, trace updates, and format/validate pipeline stage append.

## Scope (Wave 38)
Extract output-validation observability handling into trace helper and reuse in both branches.

## Objectives
1. Remove duplicated post-validation trace code from orchestrator.
2. Preserve branch-specific behavior (retry LLM call trace only in full-path).
3. Keep output validation metadata and pipeline stage markers unchanged.

## Technical Design
Add helper in `adaptive_runtime/trace_helpers.py`:
- `_apply_output_validation_observability(...)`

Update `answer_adaptive.py`:
- replace duplicated post-validation blocks with helper call in fast/full paths.

## Test Plan
Targeted:
- `tests/integration/test_adaptive_stream_contract.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_pipeline_without_sd.py`
- `tests/regression/test_streaming_sd_runtime_disabled_contract.py`
- `tests/test_sse_payload.py`

Full:
- `pytest -q tests --maxfail=1`
