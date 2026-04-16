# PRD-049: `answer_adaptive.py` Modularization (Wave 35)

## Context
State-context assembly before LLM generation still contained inline suffix composition (phase8/practice) in the main orchestrator.

## Scope (Wave 35)
Extract state-context composition with optional suffixes into state helper.

## Objectives
1. Reduce pre-LLM context assembly noise in `answer_adaptive.py`.
2. Preserve exact state-context composition order.
3. Keep phase8 and practice suffix behavior unchanged.

## Technical Design
Extend `adaptive_runtime/state_helpers.py` with:
- `_compose_state_context(...)`

Update `answer_adaptive.py`:
- replace inline state-context build + suffix append block with helper call

## Test Plan
Targeted:
- `tests/integration/test_adaptive_stream_contract.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_pipeline_without_sd.py`
- `tests/regression/test_streaming_sd_runtime_disabled_contract.py`
- `tests/test_sse_payload.py`

Full:
- `pytest -q tests`

