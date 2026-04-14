# PRD-058: `answer_adaptive.py` Modularization (Wave 44)

## Context
Fast-path and full-path branches duplicated post-LLM formatting and output-validation flow (formatter, validation retry generation, and validation observability wiring).

## Scope (Wave 44)
Extract shared post-LLM formatting+validation flow into runtime helper and reuse in both branches.

## Objectives
1. Remove duplicated format/validation code in orchestrator.
2. Preserve validation contract and retry behavior.
3. Keep branch-specific retry LLM trace behavior unchanged.

## Technical Design
Add helper in `adaptive_runtime/runtime_misc_helpers.py`:
- `_format_and_validate_llm_answer(...)`

Update `answer_adaptive.py`:
- replace fast-path duplicated post-LLM block with helper call
- replace full-path duplicated post-LLM block with helper call

## Test Plan
Targeted:
- `tests/integration/test_adaptive_stream_contract.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_pipeline_without_sd.py`
- `tests/regression/test_streaming_sd_runtime_disabled_contract.py`
- `tests/test_sse_payload.py`

Full:
- `pytest -q tests --maxfail=1`
