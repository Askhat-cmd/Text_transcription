# PRD-034: `answer_adaptive.py` Modularization (Wave 20)

## Context
Prompt preview generation for trace (`system/user`) was duplicated in fast-path and full-path branches.

## Scope (Wave 20)
Extract unified prompt-preview preparation helper and reuse it in both branches while preserving compatibility exports.

## Objectives
1. Remove duplicated prompt preview assembly code.
2. Keep debug trace prompt payload behavior unchanged.
3. Preserve module-level compatibility touchpoints used by regression tests.

## Technical Design
Add helper in `adaptive_runtime/trace_helpers.py`:
- `_prepare_llm_prompt_previews(...)`

Update `answer_adaptive.py` to:
- call `_prepare_llm_prompt_previews(...)` in fast/full branches
- keep `_build_llm_prompts` import exposed for compatibility contract

## Test Plan
Targeted:
- `tests/integration/test_adaptive_stream_contract.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_pipeline_without_sd.py`
- `tests/regression/test_streaming_sd_runtime_disabled_contract.py`
- `tests/test_sse_payload.py`

Full:
- `pytest -q tests`
