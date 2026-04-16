# PRD-025: `answer_adaptive.py` Modularization (Wave 11)

## Context
Success-path memory persistence and session summary logic remained verbose and duplicated orchestration responsibilities.

## Scope (Wave 11)
Extract persistence and response-source building helpers into `adaptive_runtime/response_utils.py (removed in Wave 142)` and wire them in success/partial paths.

## Objectives
1. Keep orchestration focused on flow control.
2. Preserve behavior for success and partial paths.
3. Keep contracts unchanged.

## Technical Design
Add helpers:
- `_persist_turn(...)` (strict persistence)
- `_save_session_summary_best_effort(...)`
- `_build_sources_from_blocks(...)`

Apply in `answer_adaptive.py`:
- Fast-path success turn persistence.
- Partial/no-blocks turn persistence.
- Full success turn persistence.
- Full success session summary write.
- Full success sources serialization.

## Test Plan
Targeted:
- `tests/integration/test_adaptive_stream_contract.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_pipeline_without_sd.py`
- `tests/regression/test_streaming_sd_runtime_disabled_contract.py`
- `tests/test_sse_payload.py`

Full:
- `pytest -q tests`

