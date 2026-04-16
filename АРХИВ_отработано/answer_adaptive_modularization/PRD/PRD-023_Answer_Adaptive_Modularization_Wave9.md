# PRD-023: `answer_adaptive.py` Modularization (Wave 9)

## Context
After Wave 8, `answer_adaptive.py` still carried large inline metadata dict construction for success payloads (fast-path and full-path).

## Scope (Wave 9)
Extract success-metadata builders to `adaptive_runtime/response_utils.py (removed in Wave 142)` and replace inline dicts in `answer_adaptive.py`.

## Objectives
1. Reduce orchestration weight in `answer_adaptive.py`.
2. Keep response contract stable.
3. Preserve legacy metadata fields (including fields later stripped for compatibility paths).

## Technical Design
Add helpers in `response_utils.py (removed in Wave 142)`:
- `_build_fast_success_metadata(...)`
- `_build_full_success_metadata(...)`

Wire both in `answer_adaptive.py` as metadata providers for `_build_success_response(...)`.

## Tasks
1. Add fast/full metadata helper builders.
2. Integrate fast-path metadata helper.
3. Integrate full-path metadata helper.
4. Run targeted tests.
5. Run full suite.
6. Update Wave 9 tasklist snapshot.

## Test Plan
Targeted:
- `tests/integration/test_adaptive_stream_contract.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_pipeline_without_sd.py`
- `tests/regression/test_streaming_sd_runtime_disabled_contract.py`
- `tests/test_sse_payload.py`

Full:
- `pytest -q tests`

