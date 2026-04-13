# PRD-016: `answer_adaptive.py` Modularization (Wave 2)

## Context
Wave 1 extracted low-risk utilities and reduced monolith size. `answer_adaptive.py` is still very large and mixes orchestration with state/runtime helper logic.

## Scope (Wave 2)
Extract state/runtime helper layer into dedicated module:
- fallback state/sd helpers
- state context + working state builders
- fast-path detection/build helpers
- async classify wrapper

Keep public API and runtime behavior unchanged.

Out of scope:
- route decision algorithm changes
- retrieval/rerank behavior changes
- API/SSE contract changes
- prompt policy changes

## Objectives
1. Reduce `answer_adaptive.py` local complexity.
2. Establish explicit state/runtime helper boundary.
3. Keep behavior and contracts identical.

## Technical Design
Add module:
- `bot_agent/adaptive_runtime/state_helpers.py`

Move implementations from `answer_adaptive.py` into module and keep thin local proxy functions for backward compatibility in current wave.

## Tasks
1. Create Wave 2 PRD/tasklist.
2. Add `state_helpers.py` with extracted implementations.
3. Switch `answer_adaptive.py` to import + proxy wrappers.
4. Run targeted adaptive/streaming contract tests.
5. Run full `pytest -q tests`.
6. Update tasklist with factual results.

## Checks
- `answer_question_adaptive(...)` signature unchanged.
- `/api/v1/questions/adaptive` contract unchanged.
- trace payload shape unchanged.
- no regression in fast-path/state flow.

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
- Revert Wave 2 commit only.
- No migrations/data changes.

## Acceptance Criteria
1. Green targeted + full tests.
2. `answer_adaptive.py` reduced and easier to read.
3. New state/runtime helper module is active in imports.
