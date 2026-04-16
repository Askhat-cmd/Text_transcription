# PRD-065: `answer_adaptive.py` Modularization (Wave 51)

## Context
After Wave 50, stage-4 in `answer_adaptive.py` still had a sizable inline orchestration block: LLM generation cycle call, LLM error branch, and output formatting/validation pipeline.

## Scope (Wave 51)
Extract stage-4 LLM orchestration into `runtime_misc_helpers` with callback-based orchestration.

## Objectives
1. Reduce LLM-stage inline complexity in `answer_adaptive.py`.
2. Preserve error-path behavior and failure trace contract.
3. Preserve output formatting/validation behavior and metadata integrity.

## Technical Design
Update `adaptive_runtime/runtime_misc_helpers.py`:
- add `_execute_full_path_llm_stage(...)` as a high-level orchestrator that:
  - runs generation via callback,
  - handles LLM error branch via callback,
  - runs formatting/validation via callback,
  - returns normalized stage payload.

Update `answer_adaptive.py`:
- import runtime helper alias and add compatibility wrapper,
- replace inline LLM generation + error/validation branch with helper call,
- keep downstream post-LLM artifact flow unchanged.

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
