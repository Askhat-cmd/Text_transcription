# PRD-018: `answer_adaptive.py` Modularization (Wave 4)

## Context
Waves 2-3 extracted state helpers. The monolith still keeps mode/feature/policy glue logic near orchestrator.

## Scope (Wave 4)
Extract mode + output-policy helper layer:
- `resolve_mode_prompt`
- `_derive_informational_mode_hint`
- feature-toggle wrappers
- `_apply_output_validation_policy`

Keep behavior and contracts identical.

## Out of Scope
- generation policy changes
- routing algorithm changes
- API/SSE schema changes

## Objectives
1. Reduce local complexity of `answer_adaptive.py`.
2. Isolate mode/policy helpers for easier maintenance.
3. Preserve all runtime outputs.

## Technical Design
Add module:
- `bot_agent/adaptive_runtime/mode_policy_helpers.py`

In `answer_adaptive.py` keep thin proxies and keep call sites stable.

## Tasks
1. Create PRD/tasklist docs for Wave 4.
2. Implement `mode_policy_helpers.py`.
3. Switch local helpers to proxies.
4. Run targeted tests.
5. Run full suite.
6. Update tasklist with factual snapshot.

## Checks
- no contract drift in adaptive endpoint.
- no trace schema drift.
- tests remain green.

## Test Plan
Targeted:
- `tests/integration/test_adaptive_stream_contract.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_pipeline_without_sd.py`
- `tests/regression/test_streaming_sd_runtime_disabled_contract.py`
- `tests/test_sse_payload.py`

Full:
- `pytest -q tests`
