# PRD-077: `answer_adaptive.py` Modularization (Wave 63)

## Context
After Wave 62, `answer_adaptive.py` still contained dead locals and stale imports accumulated from previous extraction waves.

## Scope (Wave 63)
Perform safe hygiene cleanup: remove unused imports and unused local assignments without changing runtime behavior.

## Objectives
1. Reduce noise in active orchestration module.
2. Keep compatibility touchpoints and runtime contracts unchanged.
3. Confirm zero behavior drift with full regression suite.

## Technical Design
Update `answer_adaptive.py`:
- remove unused imports:
  - `asyncio`, `json`
  - `Block`, `graph_client`, `UserState`, `WorkingState`
- remove unused local assignments from stage payload unpacking:
  - `informational_mode_hint`
  - `use_new_diagnostics_v1`
  - `rerank_mode`
  - `conditional_reranker`

No logic branch or output schema changes.

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
