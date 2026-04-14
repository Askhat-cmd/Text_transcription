# PRD-062: `answer_adaptive.py` Modularization (Wave 48)

## Context
After Wave 47, a substantial inline block remained in stage-3 for routing result resolution, confidence cap application, informational mode derivation, and mode directive preparation.

## Scope (Wave 48)
Extract routing+block-cap orchestration into routing runtime helper.

## Objectives
1. Reduce routing-related inline complexity in `answer_adaptive.py`.
2. Preserve deterministic/non-deterministic route behavior.
3. Preserve cap/mode-directive outputs for downstream prompt and trace flow.

## Technical Design
Update `adaptive_runtime/routing_stage_helpers.py`:
- add `_resolve_routing_and_apply_block_cap(...)`.

Update `answer_adaptive.py`:
- import runtime helper alias,
- add compatibility wrapper,
- replace inline routing/cap block with helper call and artifact mapping.

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
