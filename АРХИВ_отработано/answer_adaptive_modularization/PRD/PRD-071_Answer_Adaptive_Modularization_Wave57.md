# PRD-071: `answer_adaptive.py` Modularization (Wave 57)

## Context
After Wave 56, stage-2/pre-routing setup in `answer_adaptive.py` still contained a dense orchestration sequence (state analysis, diagnostics, contradiction handling, and pre-routing decision), despite having lower-level helpers.

## Scope (Wave 57)
Extract stage-2 + pre-routing orchestration into routing runtime helper.

## Objectives
1. Reduce early-pipeline orchestration complexity in `answer_adaptive.py`.
2. Preserve diagnostics/pre-routing behavior and debug trace contracts.
3. Keep fast-path and full-path downstream contracts unchanged.

## Technical Design
Update `adaptive_runtime/routing_stage_helpers.py`:
- add `_run_state_and_pre_routing_pipeline(...)` high-level orchestrator that composes:
  - `_run_state_analysis_stage(...)`
  - `_compute_diagnostics_v1(...)`
  - `_build_contradiction_payload(...)`
  - `_resolve_pre_routing(...)`

Update `answer_adaptive.py`:
- import new helpers and add compatibility wrappers,
- replace inline stage-2/pre-routing orchestration block with high-level helper call,
- switch fast-path branch to already extracted `_run_fast_path_stage(...)` helper path,
- remove dead wrappers/import aliases replaced by the new path.

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
