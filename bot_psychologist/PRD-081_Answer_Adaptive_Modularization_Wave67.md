# PRD-081: `answer_adaptive.py` Modularization (Wave 67)

## Context
After recent extraction waves, `answer_adaptive.py` retained one stale import from retrieval helpers that was no longer used in active orchestration.

## Scope (Wave 67)
Remove dead retrieval helper import and validate no regression.

## Objectives
1. Keep import surface aligned with actual usage.
2. Avoid drift/noise during ongoing modularization.
3. Preserve runtime behavior and contracts.

## Technical Design
Update `answer_adaptive.py`:
- remove unused import alias:
  - `_run_retrieval_and_rerank_stage as _runtime_run_retrieval_and_rerank_stage`

No logic changes.

## Test Plan
Expanded targeted:
- `tests/regression/test_no_level_based_prompting.py`
- `tests/test_retrieval_pipeline_simplified.py`
- `tests/integration/test_degraded_mode_without_retrieval.py`
- `tests/e2e/test_degraded_retrieval_case.py`
- `tests/integration/test_sparse_output_triggers_regeneration_hint.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_routing_recalibration_for_exploratory_queries.py`
- `tests/integration/test_adaptive_stream_contract.py`
- `tests/test_sse_payload.py`
- `tests/unit/test_curious_not_auto_informational.py`
- `tests/unit/test_user_level_adapter_removed.py`
- `tests/unit/test_sd_legacy_final_cleanup_prompt_context.py`
- `tests/unit/test_query_is_passed_to_output_validation_policy_v1031.py`
- `tests/integration/test_generation_validation_separation.py`

Full:
- `pytest -q tests --maxfail=1`
