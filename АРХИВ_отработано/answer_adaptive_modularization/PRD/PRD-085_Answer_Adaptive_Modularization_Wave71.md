# PRD-085: `answer_adaptive.py` Modularization (Wave 71)

## Context
Two more runtime boundaries still used callable wrappers for a static per-request flag (`informational_branch_enabled`): bootstrap onboarding guard and retrieval routing cap.

## Scope (Wave 71)
Replace these callable injections with direct boolean contracts.

## Objectives
1. Reduce ad-hoc lambda wrappers in orchestration.
2. Keep behavior identical while simplifying APIs.
3. Confirm stability via targeted + full test suites.

## Technical Design
Update `bot_agent/adaptive_runtime/runtime_misc_helpers.py`:
- in `_run_bootstrap_and_onboarding_guard(...)`:
  - replace `informational_branch_enabled_fn` with `informational_branch_enabled: bool`
  - use direct boolean check for `start_command_response`

Update `bot_agent/adaptive_runtime/routing_stage_helpers.py`:
- in `_resolve_routing_and_apply_block_cap(...)`:
  - replace `informational_branch_enabled_fn: Callable[[], bool]` with `informational_branch_enabled: bool`
  - compute `informational_mode` from bool directly

Update `bot_agent/adaptive_runtime/retrieval_stage_helpers.py`:
- update call into `_resolve_routing_and_apply_block_cap(...)` to pass bool directly.

Update `bot_agent/answer_adaptive.py`:
- update bootstrap call into `_runtime_run_bootstrap_and_onboarding_guard(...)` to pass bool directly.

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
