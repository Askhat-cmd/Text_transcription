# PRD-117: `answer_adaptive.py` Modularization (Wave 103)

## Context
Bootstrap path still received user-level resolver callback from facade, though resolver is runtime-stable in state helpers.

## Scope (Wave 103)
Localize user-level resolver in runtime bootstrap helper and remove obsolete callback from facade call.

## Objectives
1. Continue shrinking callback surface in bootstrap orchestration.
2. Preserve user-level normalization behavior.
3. Maintain full regression green state.

## Technical Design
Update `bot_agent/adaptive_runtime/runtime_misc_helpers.py`:
- remove `_run_bootstrap_and_onboarding_guard(...): resolve_path_user_level_fn`
- localize import `_resolve_path_user_level` from `state_helpers`
- keep return payload (`path_level_enum`) unchanged

Update `bot_agent/answer_adaptive.py`:
- remove obsolete call arg:
  - `resolve_path_user_level_fn=_resolve_path_user_level`

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
