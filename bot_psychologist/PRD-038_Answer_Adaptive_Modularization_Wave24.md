# PRD-038: `answer_adaptive.py` Modularization (Wave 24)

## Context
Token extraction and session metrics update from `llm_result` were duplicated in fast-path and full-path success flows.

## Scope (Wave 24)
Extract shared helper for collecting LLM token/session metrics and reuse in both branches.

## Objectives
1. Remove duplicated token/session metrics code.
2. Keep session accounting behavior unchanged.
3. Preserve downstream trace and success payload fields.

## Technical Design
Add helper in `adaptive_runtime/runtime_misc_helpers.py`:
- `_collect_llm_session_metrics(...)`

Update `answer_adaptive.py`:
- replace two duplicated token/session blocks with helper usage

## Test Plan
Targeted:
- `tests/integration/test_adaptive_stream_contract.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_pipeline_without_sd.py`
- `tests/regression/test_streaming_sd_runtime_disabled_contract.py`
- `tests/test_sse_payload.py`

Full:
- `pytest -q tests`
