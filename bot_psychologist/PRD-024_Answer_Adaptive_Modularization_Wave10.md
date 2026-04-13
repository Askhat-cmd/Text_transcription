# PRD-024: `answer_adaptive.py` Modularization (Wave 10)

## Context
Error/exception handling still had inline payload construction and repeated best-effort memory persistence snippets.

## Scope (Wave 10)
1. Reuse `_build_error_response(...)` for unhandled exception path.
2. Introduce shared helper for best-effort memory turn persistence.
3. Apply helper in error paths that already used non-fatal `try/except` persistence.

## Objectives
1. Remove repetitive error-path boilerplate.
2. Preserve error response contract.
3. Keep failure handling non-fatal and stable.

## Technical Design
- Add in `adaptive_runtime/response_utils.py`:
  - `_persist_turn_best_effort(...)`
- Update `answer_adaptive.py`:
  - `except Exception` branch uses `_build_error_response(...)` + existing metadata shape.
  - LLM-error and exception paths use `_persist_turn_best_effort(...)`.

## Tasks
1. Add shared persistence helper.
2. Refactor LLM-error path to use shared persistence helper.
3. Refactor unhandled-exception response path to `_build_error_response`.
4. Keep metadata/user_id compatibility in exception response.
5. Run targeted tests.
6. Run full suite.

## Test Plan
Targeted:
- `tests/integration/test_adaptive_stream_contract.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_pipeline_without_sd.py`
- `tests/regression/test_streaming_sd_runtime_disabled_contract.py`
- `tests/test_sse_payload.py`

Full:
- `pytest -q tests`
