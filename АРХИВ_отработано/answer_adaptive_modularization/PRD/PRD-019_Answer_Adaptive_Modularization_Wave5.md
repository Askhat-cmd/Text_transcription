# PRD-019: `answer_adaptive.py` Modularization (Wave 5)

## Context
After Wave 4, `answer_adaptive.py` still contains runtime misc helpers that are not part of orchestration logic.

## Scope (Wave 5)
Extract runtime misc helpers:
- `_estimate_cost` + pricing table
- `_sd_runtime_disabled`
- `_build_start_command_response`

Keep behavior/contracts unchanged.

## Objectives
1. Shrink monolith further.
2. Isolate reusable runtime utility behavior.
3. Preserve API/SSE/trace outputs.

## Technical Design
Add module:
- `bot_agent/adaptive_runtime/runtime_misc_helpers.py`

`answer_adaptive.py` keeps thin proxies only.

## Tasks
1. Create Wave 5 PRD/tasklist docs.
2. Add `runtime_misc_helpers.py`.
3. Replace local implementations with proxies.
4. Run targeted tests.
5. Run full test suite.
6. Update tasklist with real metrics.

## Test Plan
Targeted:
- `tests/integration/test_adaptive_stream_contract.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_pipeline_without_sd.py`
- `tests/regression/test_streaming_sd_runtime_disabled_contract.py`
- `tests/test_sse_payload.py`

Full:
- `pytest -q tests`
