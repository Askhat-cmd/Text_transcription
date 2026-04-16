# PRD-031: `answer_adaptive.py` Modularization (Wave 17)

## Context
Fast-path branch still had verbose inline debug bootstrap and mode-directive prompt prep blocks.

## Scope (Wave 17)
Extract fast-path bootstrap helpers in routing stage module and replace inline blocks.

## Objectives
1. Reduce fast-path branch verbosity.
2. Preserve fast-path trace payload contract.
3. Preserve mode directive behavior.

## Technical Design
Add helpers in `adaptive_runtime/routing_stage_helpers.py`:
- `_apply_fast_path_debug_bootstrap(...)`
- `_build_fast_path_mode_directive(...)`

Use both from `answer_adaptive.py`.

## Test Plan
Targeted:
- `tests/integration/test_adaptive_stream_contract.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_pipeline_without_sd.py`
- `tests/regression/test_streaming_sd_runtime_disabled_contract.py`
- `tests/test_sse_payload.py`

Full:
- `pytest -q tests`
