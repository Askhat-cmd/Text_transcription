# PRD-100: `answer_adaptive.py` Modularization (Wave 86)

## Context
Fast-path stage still accepted onboarding instruction-builder dependencies from `answer_adaptive.py`, although these builders are stable onboarding internals.

## Scope (Wave 86)
Narrow `_run_fast_path_stage(...)` by localizing onboarding instruction builders inside runtime helper.

## Objectives
1. Reduce fast-path facade call surface.
2. Keep phase8 context suffix behavior unchanged.
3. Validate with expanded targeted and full suites.

## Technical Design
Update `bot_agent/adaptive_runtime/runtime_misc_helpers.py`:
- remove `_run_fast_path_stage(...)` params:
  - `build_first_turn_instruction_fn`
  - `build_mixed_query_instruction_fn`
  - `build_user_correction_instruction_fn`
  - `build_informational_guardrail_instruction_fn`
- local import from `onboarding_flow` and pass localized builders into `build_phase8_context_suffix_fn(...)`.

Update `bot_agent/answer_adaptive.py`:
- remove obsolete fast-path call args listed above.
- remove now-unused onboarding builder imports.

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
