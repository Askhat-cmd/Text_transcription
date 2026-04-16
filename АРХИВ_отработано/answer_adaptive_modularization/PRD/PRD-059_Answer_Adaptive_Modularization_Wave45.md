# PRD-059: `answer_adaptive.py` Modularization (Wave 45)

## Context
Stage 2 state-analysis setup remained inline in orchestrator: conversation history preparation, debug/non-debug classification path, fallback policy, and initial debug payload wiring.

## Scope (Wave 45)
Extract Stage 2 state-analysis orchestration into routing runtime helper.

## Objectives
1. Reduce orchestration complexity around state-classifier stage.
2. Preserve state-analysis and informational mode contract.
3. Keep debug trace payload fields unchanged.

## Technical Design
Add helper in `adaptive_runtime/routing_stage_helpers.py`:
- `_run_state_analysis_stage(...)`

Update `answer_adaptive.py`:
- replace inline Stage 2 state-analysis block with helper call.

## Test Plan
Targeted:
- `tests/integration/test_adaptive_stream_contract.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_pipeline_without_sd.py`
- `tests/regression/test_streaming_sd_runtime_disabled_contract.py`
- `tests/test_sse_payload.py`

Full:
- `pytest -q tests --maxfail=1`
