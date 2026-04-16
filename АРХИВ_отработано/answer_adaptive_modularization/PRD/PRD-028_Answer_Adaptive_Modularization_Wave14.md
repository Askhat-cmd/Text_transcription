# PRD-028: `answer_adaptive.py` Modularization (Wave 14)

## Context
Function-level initialization still contained large inline setup blocks for debug payloads and Stage 1 runtime context loading.

## Scope (Wave 14)
Extract initialization helpers for:
- debug payload bootstrap
- Stage 1 runtime memory/context loading

## Objectives
1. Make orchestration entry cleaner.
2. Isolate Stage 1 loading details into dedicated helper.
3. Preserve behavior and trace contract.

## Technical Design
Add helpers:
- `trace_helpers._init_debug_payloads(...)`
- `runtime_misc_helpers._load_runtime_memory_context(...)`

Use both in `answer_adaptive.answer_question_adaptive(...)`.

## Test Plan
Targeted:
- `tests/integration/test_adaptive_stream_contract.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_pipeline_without_sd.py`
- `tests/regression/test_streaming_sd_runtime_disabled_contract.py`
- `tests/test_sse_payload.py`

Full:
- `pytest -q tests`
