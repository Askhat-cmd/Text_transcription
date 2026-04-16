# PRD-069: `answer_adaptive.py` Modularization (Wave 55)

## Context
After Wave 54, `answer_adaptive.py` still contained compatibility wrappers/imports for intermediate orchestrators that were no longer used by the active pipeline.

## Scope (Wave 55)
Remove dead local wrappers/import aliases in `answer_adaptive.py` after successful migration to higher-level helpers.

## Objectives
1. Reduce local API surface in `answer_adaptive.py`.
2. Remove unused imports/wrappers without changing behavior.
3. Keep runtime modules backward-safe while simplifying active entrypoint.

## Technical Design
Update `answer_adaptive.py`:
- remove unused response-utils alias: `_runtime_finalize_full_path_success_stage`.
- remove unused runtime-misc alias: `_runtime_execute_full_path_llm_stage`.
- remove unused local wrapper functions:
  - `_execute_full_path_llm_stage(...)`
  - `_finalize_full_path_success_stage(...)`

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
