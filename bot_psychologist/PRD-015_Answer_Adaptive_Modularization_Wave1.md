# PRD-015: `answer_adaptive.py` Modularization (Wave 1)

## Context
`bot_agent/answer_adaptive.py` is too large for safe iterative maintenance. We need to begin modularization with zero behavioral drift.

## Scope (Wave 1)
Safe extraction of helper logic only:
- trace/pipeline utility helpers
- shared response helper builders
- keep entrypoint and orchestration in place

Out of scope:
- route decision changes
- diagnostics policy changes
- API schema changes
- SSE transport changes

## Objectives
1. Reduce local complexity of `answer_adaptive.py`.
2. Establish new internal module namespace for next waves.
3. Preserve exact runtime behavior.

## Technical Design
Create package:
- `bot_agent/adaptive_runtime/__init__.py`
- `bot_agent/adaptive_runtime/pipeline_utils.py`
- `bot_agent/adaptive_runtime/response_utils.py`

Move low-risk helpers from `answer_adaptive.py` into these modules and import them back.

## Tasks
1. Create `adaptive_runtime` package and helper modules.
2. Move safe helper functions (no contract changes).
3. Keep original call sites compatible in `answer_adaptive.py`.
4. Run targeted tests.
5. Run full test suite.
6. Update tasklist status.

## Checks
- `answer_question_adaptive` signature unchanged.
- `/api/v1/questions/adaptive` behavior unchanged.
- trace keys unaffected.
- no new failing tests.

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
- Revert Wave 1 commit(s) only.
- No data/schema migration involved.

## Acceptance Criteria
1. Full tests green.
2. `answer_adaptive.py` reduced and cleaner.
3. New module boundaries in place for Wave 2.

