# PRD-080: `answer_adaptive.py` Modularization (Wave 66)

## Context
After Wave 65, orchestration remained correct but repeatedly recomputed stable runtime values (`LLM_MODEL` string and feature-flag booleans) across stages.

## Scope (Wave 66)
Introduce per-request local runtime constants and reuse them across stage calls.

## Objectives
1. Remove repeated flag/model resolution in a single request cycle.
2. Keep all behavior and contracts unchanged.
3. Improve readability of stage-call wiring.

## Technical Design
Update `answer_adaptive.py`:
- add per-request locals near request start:
  - `llm_model_name`
  - `prompt_stack_enabled`
  - `output_validation_enabled`
  - `informational_branch_enabled`
  - `diagnostics_v1_enabled`
  - `deterministic_route_resolver_enabled`
- replace repeated inline calls in stage invocations with these locals.

No branch/contract changes.

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
