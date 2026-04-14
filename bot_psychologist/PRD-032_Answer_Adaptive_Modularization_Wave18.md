# PRD-032: `answer_adaptive.py` Modularization (Wave 18)

## Context
Both fast-path and full-path branches still duplicated phase8 suffix assembly and informational mode prompt selection logic.

## Scope (Wave 18)
Extract reusable helpers for phase8 context composition and mode prompt selection into routing-stage helper module and replace duplicated inline blocks.

## Objectives
1. Remove duplicated phase8 instruction assembly.
2. Standardize informational-mode state-context prompt resolution.
3. Keep runtime behavior and trace contract unchanged.

## Technical Design
Add helpers in `adaptive_runtime/routing_stage_helpers.py`:
- `_build_state_context_mode_prompt(...)`
- `_build_phase8_context_suffix(...)`

Update `answer_adaptive.py` to use these helpers in:
- fast-path branch
- full-path branch

## Test Plan
Targeted:
- `tests/integration/test_adaptive_stream_contract.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_pipeline_without_sd.py`
- `tests/regression/test_streaming_sd_runtime_disabled_contract.py`
- `tests/test_sse_payload.py`

Full:
- `pytest -q tests`
