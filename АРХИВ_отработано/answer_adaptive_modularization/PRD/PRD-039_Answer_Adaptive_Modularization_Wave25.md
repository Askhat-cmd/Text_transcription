# PRD-039: `answer_adaptive.py` Modularization (Wave 25)

## Context
`prompt_stack_v2` override/meta construction was duplicated in fast-path and full-path generation blocks.

## Scope (Wave 25)
Extract shared prompt-stack build helper and reuse it in both branches.

## Objectives
1. Remove duplicated `prompt_registry_v2.build(...)` orchestration code.
2. Keep prompt-stack metadata and override behavior unchanged.
3. Preserve phase8/correction flags propagation.

## Technical Design
Add helper in `adaptive_runtime/runtime_misc_helpers.py`:
- `_build_prompt_stack_override(...)`

Update `answer_adaptive.py`:
- replace fast-path duplicated prompt-stack block
- replace full-path duplicated prompt-stack block

## Test Plan
Targeted:
- `tests/integration/test_adaptive_stream_contract.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_pipeline_without_sd.py`
- `tests/regression/test_streaming_sd_runtime_disabled_contract.py`
- `tests/test_sse_payload.py`

Full:
- `pytest -q tests`
