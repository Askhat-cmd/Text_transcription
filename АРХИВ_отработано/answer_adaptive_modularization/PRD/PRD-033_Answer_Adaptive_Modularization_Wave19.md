# PRD-033: `answer_adaptive.py` Modularization (Wave 19)

## Context
Fast-path and full-path branches still duplicated LLM generation stage orchestration (generate call, trace attachment, pipeline timing).

## Scope (Wave 19)
Extract unified LLM stage helper and replace duplicated generate/trace blocks in both branches.

## Objectives
1. Reduce duplicated LLM stage code in orchestrator.
2. Preserve trace payload and timing contract.
3. Keep retry-validation logic untouched.

## Technical Design
Add helper in `adaptive_runtime/runtime_misc_helpers.py`:
- `_generate_llm_with_trace(...)`

Update `answer_adaptive.py` to call this helper in:
- fast-path branch
- full-path branch

## Test Plan
Targeted:
- `tests/integration/test_adaptive_stream_contract.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_pipeline_without_sd.py`
- `tests/regression/test_streaming_sd_runtime_disabled_contract.py`
- `tests/test_sse_payload.py`

Full:
- `pytest -q tests`
