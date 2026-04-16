# PRD-053: `answer_adaptive.py` Modularization (Wave 39)

## Context
Prompt-stack setup, LLM prompt preview generation, and LLM call execution were duplicated between fast-path and full-path branches.

## Scope (Wave 39)
Extract combined prompt-stack + preview + generation cycle into runtime helper and reuse in both branches.

## Objectives
1. Remove large duplicated LLM preflight/generation block from orchestrator.
2. Preserve prompt-stack behavior and trace payload (`prompt_stack_v2`, `llm_calls`).
3. Keep retry path behavior unchanged by returning `response_generator` for downstream validation-retry.

## Technical Design
Add helper in `adaptive_runtime/runtime_misc_helpers.py`:
- `_run_llm_generation_cycle(...)`

Update `answer_adaptive.py`:
- replace fast-path duplicated block with helper call
- replace full-path duplicated block with helper call

## Test Plan
Targeted:
- `tests/integration/test_adaptive_stream_contract.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_pipeline_without_sd.py`
- `tests/regression/test_streaming_sd_runtime_disabled_contract.py`
- `tests/test_sse_payload.py`

Full:
- `pytest -q tests --maxfail=1`
