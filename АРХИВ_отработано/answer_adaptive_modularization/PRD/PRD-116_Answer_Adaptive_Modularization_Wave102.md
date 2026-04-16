# PRD-116: `answer_adaptive.py` Modularization (Wave 102)

## Context
Bootstrap stage still accepted two facade-provided callbacks that are runtime-stable:
- start-command response builder
- memory debug payload applier

## Scope (Wave 102)
Localize these callbacks in `runtime_misc_helpers.py` and keep facade orchestration thinner.

## Objectives
1. Reduce callback surface in bootstrap call.
2. Preserve onboarding start-command behavior and debug trace output.
3. Keep full test matrix green.

## Technical Design
Update `bot_agent/adaptive_runtime/runtime_misc_helpers.py`:
- remove args from `_run_bootstrap_and_onboarding_guard(...)`:
  - `build_start_command_response_fn`
  - `apply_memory_debug_info_fn`
- localize runtime wiring:
  - call `_build_start_command_response(...)` directly
  - import and call `_apply_memory_debug_info` directly
- pass `logger` into helper for consistent logging behavior.

Update `bot_agent/answer_adaptive.py`:
- remove bootstrap lambda and obsolete callback args.
- remove now-unused imports tied to removed callbacks.
- pass `logger=logger` into bootstrap helper.

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
