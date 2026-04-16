# PRD-044: `answer_adaptive.py` Modularization (Wave 30)

## Context
Practice-selection orchestration (route policy checks, selector call, metadata update, and context suffix construction) remained inline inside Stage 3 full-path flow.

## Scope (Wave 30)
Extract practice-selection and context-suffix assembly into routing-stage helper.

## Objectives
1. Reduce Stage 3 inline branching and side-effect density.
2. Preserve practice routing policy and memory metadata behavior.
3. Keep trace payload fields unchanged.

## Technical Design
Extend `adaptive_runtime/routing_stage_helpers.py` with:
- `_resolve_practice_selection_context(...)`

Update `answer_adaptive.py`:
- replace inline practice-selection block with helper call
- keep downstream trace assignment and state-context append unchanged

## Test Plan
Targeted:
- `tests/integration/test_adaptive_stream_contract.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_pipeline_without_sd.py`
- `tests/regression/test_streaming_sd_runtime_disabled_contract.py`
- `tests/test_sse_payload.py`

Full:
- `pytest -q tests`

