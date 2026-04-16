# PRD-063: `answer_adaptive.py` Modularization (Wave 49)

## Context
After Wave 48, the stage-3 branch still kept inline orchestration for Phase-8 suffix assembly, practice-selection context, routing trace attachment, and runtime context refresh.

## Scope (Wave 49)
Extract post-routing context/trace orchestration into a dedicated routing runtime helper.

## Objectives
1. Reduce mid-pipeline inline complexity in `answer_adaptive.py`.
2. Preserve phase-8 suffix and practice context behavior.
3. Preserve routing trace/debug payload contract and context refresh behavior.

## Technical Design
Update `adaptive_runtime/routing_stage_helpers.py`:
- add `_finalize_routing_context_and_trace(...)` to wrap:
  - phase-8 context suffix assembly,
  - practice selection context,
  - routing-stage trace attachment,
  - conversation-context refresh.

Update `answer_adaptive.py`:
- import runtime helper alias,
- add compatibility wrapper,
- replace inline post-routing block with helper call and return-value mapping.

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
