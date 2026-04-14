# PRD-064: `answer_adaptive.py` Modularization (Wave 50)

## Context
After Wave 49, an inline post-cap retrieval block still remained in `answer_adaptive.py`: adapted block preparation, progressive feedback application, and retrieval observability wiring.

## Scope (Wave 50)
Extract adapted-blocks + observability orchestration into trace runtime helper.

## Objectives
1. Reduce stage-3 inline complexity in `answer_adaptive.py`.
2. Preserve progressive feedback behavior and debug trace fields.
3. Preserve retrieval observability payload contract.

## Technical Design
Update `adaptive_runtime/trace_helpers.py`:
- add `_prepare_adapted_blocks_and_attach_observability(...)`.

Update `adaptive_runtime/retrieval_stage_helpers.py`:
- include `progressive_rag` in return payload from `_run_retrieval_and_rerank_stage(...)` to keep downstream progressive feedback contract.

Update `answer_adaptive.py`:
- import runtime helper alias,
- add compatibility wrapper,
- replace inline adapted-blocks/observability block with helper call,
- map `progressive_rag` from retrieval stage payload.

## Test Plan
Targeted:
- `tests/test_retrieval_pipeline_simplified.py`
- `tests/integration/test_degraded_mode_without_retrieval.py`
- `tests/e2e/test_degraded_retrieval_case.py`
- `tests/integration/test_sparse_output_triggers_regeneration_hint.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_routing_recalibration_for_exploratory_queries.py`

Full:
- `pytest -q tests --maxfail=1`
