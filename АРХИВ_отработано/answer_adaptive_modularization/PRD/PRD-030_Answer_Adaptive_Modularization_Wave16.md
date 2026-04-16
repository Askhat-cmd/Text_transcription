# PRD-030: `answer_adaptive.py` Modularization (Wave 16)

## Context
Stage 2 classification/routing pre-resolution had a long inline block for diagnostics_v1, contradiction handling and pre-routing fast-path decision.

## Scope (Wave 16)
Extract Stage 2 pre-routing preparation into dedicated helper module.

## Objectives
1. Shrink Stage 2 orchestration block in `answer_adaptive.py`.
2. Preserve routing semantics and debug contracts.
3. Keep deterministic/non-deterministic routing behavior unchanged.

## Technical Design
Add module:
- `adaptive_runtime/routing_stage_helpers.py`

Extract helpers:
- `_compute_diagnostics_v1(...)`
- `_build_contradiction_payload(...)`
- `_resolve_pre_routing(...)`

Wire these in `answer_adaptive.answer_question_adaptive(...)`.

## Test Plan
Targeted:
- `tests/integration/test_adaptive_stream_contract.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_pipeline_without_sd.py`
- `tests/regression/test_streaming_sd_runtime_disabled_contract.py`
- `tests/test_sse_payload.py`

Full:
- `pytest -q tests`
