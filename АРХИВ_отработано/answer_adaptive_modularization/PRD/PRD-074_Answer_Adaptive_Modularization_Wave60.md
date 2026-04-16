# PRD-074: `answer_adaptive.py` Modularization (Wave 60)

## Context
After Wave 59, `answer_adaptive.py` still contained a set of thin typed proxy wrappers around `_runtime_*` helpers.

## Scope (Wave 60)
Remove selected typed proxy wrappers that are not required as public/test touchpoints and switch call sites to direct runtime helper usage.

## Objectives
1. Reduce facade layer size in `answer_adaptive.py`.
2. Preserve explicit compatibility touchpoints used by tests.
3. Keep behavior unchanged under full regression suite.

## Technical Design
Update `answer_adaptive.py`:
- remove thin proxy wrappers:
  - `_derive_informational_mode_hint`, `_estimate_cost`, `_detect_fast_path_reason`, `_fallback_state_analysis`, `_sd_runtime_disabled`, `_diagnostics_v1_enabled`, `_deterministic_route_resolver_enabled`, `_prompt_stack_v2_enabled`, `_informational_branch_enabled`, `_depth_to_phase`, `_mode_to_direction`, `_derive_defense`, `_build_working_state`, `_looks_like_greeting`, `_looks_like_name_intro`, `_build_fast_path_block`.
- switch orchestration call sites to direct `_runtime_*` helpers.
- keep compatibility wrappers/touchpoints used by tests:
  - `resolve_mode_prompt`, `_fallback_sd_result`, `_output_validation_enabled`, `_apply_output_validation_policy`, `_resolve_path_user_level`, `_build_state_context`, `_should_use_fast_path`, `_classify_parallel`.
- update `_set_working_state_best_effort(...)` to bind `_runtime_build_working_state` directly.

## Test Plan
Expanded targeted:
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
