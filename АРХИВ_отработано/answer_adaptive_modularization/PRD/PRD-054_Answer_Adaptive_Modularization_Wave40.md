# PRD-054: `answer_adaptive.py` Modularization (Wave 40)

## Context
Fast-path still used inline state-context composition with manual phase8 suffix append, while full-path already relied on `_compose_state_context(...)`.

## Scope (Wave 40)
Align fast-path state-context composition with the shared helper.

## Objectives
1. Remove duplicate state-context build logic from fast-path.
2. Keep phase8 suffix behavior unchanged.
3. Preserve all fast-path contracts and trace payloads.

## Technical Design
Update `answer_adaptive.py`:
- replace fast-path `_build_state_context + manual phase8 append` with `_compose_state_context(...)`
- pass `practice_context_suffix=""` explicitly for fast-path parity

## Test Plan
Targeted:
- `tests/integration/test_adaptive_stream_contract.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_pipeline_without_sd.py`
- `tests/regression/test_streaming_sd_runtime_disabled_contract.py`
- `tests/test_sse_payload.py`

Full:
- `pytest -q tests --maxfail=1`
