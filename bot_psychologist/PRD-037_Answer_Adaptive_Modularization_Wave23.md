# PRD-037: `answer_adaptive.py` Modularization (Wave 23)

## Context
Working-state persistence had repeated `try/except` blocks across fast-path, partial, and success branches.

## Scope (Wave 23)
Extract unified best-effort working-state update helper and replace duplicated inline blocks.

## Objectives
1. Remove repeated working-state update code.
2. Preserve branch-specific warning prefixes.
3. Keep runtime behavior unchanged.

## Technical Design
Add helper in `adaptive_runtime/state_helpers.py`:
- `_set_working_state_best_effort(...)`

Update `answer_adaptive.py`:
- add local wrapper delegating to runtime helper
- replace three duplicated try/except blocks with wrapper calls

## Test Plan
Targeted:
- `tests/integration/test_adaptive_stream_contract.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_pipeline_without_sd.py`
- `tests/regression/test_streaming_sd_runtime_disabled_contract.py`
- `tests/test_sse_payload.py`

Full:
- `pytest -q tests`
