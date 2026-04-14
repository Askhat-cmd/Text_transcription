# PRD-068: `answer_adaptive.py` Modularization (Wave 54)

## Context
After Wave 53, the no-retrieval branch in `answer_adaptive.py` still contained a long parameter-heavy call with repeated stage metadata and fallback behavior.

## Scope (Wave 54)
Extract no-retrieval branch orchestration into response runtime helper.

## Objectives
1. Reduce branch complexity in `answer_adaptive.py`.
2. Preserve partial-response behavior when retrieval returns no blocks.
3. Preserve failure trace and observability contract for no-retrieval path.

## Technical Design
Update `adaptive_runtime/response_utils.py`:
- add `_run_no_retrieval_stage(...)` that wraps `_handle_no_retrieval_partial_response(...)` with stable message and skipped-stage defaults.

Update `answer_adaptive.py`:
- import runtime helper alias and add compatibility wrapper,
- replace long inline no-retrieval call with `_run_no_retrieval_stage(...)`.

## Test Plan
Targeted:
- `tests/test_retrieval_pipeline_simplified.py`
- `tests/integration/test_degraded_mode_without_retrieval.py`
- `tests/e2e/test_degraded_retrieval_case.py`
- `tests/integration/test_sparse_output_triggers_regeneration_hint.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_routing_recalibration_for_exploratory_queries.py`
- `tests/integration/test_adaptive_stream_contract.py`
- `tests/test_sse_payload.py`

Full:
- `pytest -q tests --maxfail=1`
