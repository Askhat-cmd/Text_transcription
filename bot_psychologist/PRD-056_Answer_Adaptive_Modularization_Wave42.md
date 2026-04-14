# PRD-056: `answer_adaptive.py` Modularization (Wave 42)

## Context
Full-path success finalization remained a large inline block in orchestrator: elapsed timing, sources creation, success metadata build, and success trace finalization.

## Scope (Wave 42)
Extract full-path success finalization into response runtime helper.

## Objectives
1. Reduce orchestrator size by removing full-path final block.
2. Preserve success payload, sources metadata, and trace finalization contract.
3. Keep token/cost/session fields unchanged.

## Technical Design
Add helper in `adaptive_runtime/response_utils.py`:
- `_build_full_path_success_response(...)`

Update `answer_adaptive.py`:
- replace inline full-path final success block with helper call.

## Test Plan
Targeted:
- `tests/integration/test_adaptive_stream_contract.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_pipeline_without_sd.py`
- `tests/regression/test_streaming_sd_runtime_disabled_contract.py`
- `tests/test_sse_payload.py`

Full:
- `pytest -q tests --maxfail=1`
