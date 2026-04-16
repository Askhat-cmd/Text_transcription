# PRD-017: `answer_adaptive.py` Modularization (Wave 3)

## Context
Wave 2 extracted fallback/classify/fast-path helpers into `adaptive_runtime/state_helpers.py`.
Main orchestrator is still overloaded with state-context and working-state construction helpers.

## Scope (Wave 3)
Extract state context + working-state helper layer:
- `_build_state_context`
- `_depth_to_phase`
- `_mode_to_direction`
- `_derive_defense`
- `_build_working_state`

Keep entrypoint and external contracts unchanged.

## Out of Scope
- prompt policy edits
- retrieval/rerank algorithm changes
- route resolver behavior edits
- SSE/API schema changes

## Objectives
1. Further reduce `answer_adaptive.py` complexity.
2. Consolidate state-related helper logic in one runtime module.
3. Preserve behavior exactly.

## Technical Design
- Extend `bot_agent/adaptive_runtime/state_helpers.py` with context/working-state builders.
- Keep thin proxy wrappers in `answer_adaptive.py` to avoid risky call-site rewrites.

## Tasks
1. Add Wave 3 PRD/tasklist docs.
2. Move state-context/working-state helpers to `state_helpers.py`.
3. Convert local implementations in `answer_adaptive.py` to proxy wrappers.
4. Run targeted tests.
5. Run full suite.
6. Update Wave 3 tasklist with factual metrics.

## Checks
- `answer_question_adaptive(...)` signature unchanged.
- metadata/debug_trace schema unchanged.
- no change in fast-path/state outputs.

## Test Plan
Targeted:
- `tests/integration/test_adaptive_stream_contract.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_pipeline_without_sd.py`
- `tests/regression/test_streaming_sd_runtime_disabled_contract.py`
- `tests/test_sse_payload.py`

Full:
- `pytest -q tests`

## Rollback
- Revert Wave 3 commit only.

## Acceptance Criteria
- Green targeted + full tests.
- Reduced monolith footprint.
- State helper boundary cleaner for next wave.
