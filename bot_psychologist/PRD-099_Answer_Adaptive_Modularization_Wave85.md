# PRD-099: `answer_adaptive.py` Modularization (Wave 85)

## Context
Stage-3 retrieval/routing context still accepted onboarding instruction-builder functions from `answer_adaptive.py`. These builders are stable onboarding helpers and can be localized in retrieval runtime helper.

## Scope (Wave 85)
Narrow `_run_retrieval_routing_context_stage(...)` by localizing onboarding instruction builders.

## Objectives
1. Reduce Stage-3 facade call surface in `answer_adaptive.py`.
2. Preserve phase8/context suffix behavior.
3. Validate with expanded targeted and full suites.

## Technical Design
Update `bot_agent/adaptive_runtime/retrieval_stage_helpers.py`:
- remove params from `_run_retrieval_routing_context_stage(...)`:
  - `build_first_turn_instruction_fn`
  - `build_mixed_query_instruction_fn`
  - `build_user_correction_instruction_fn`
  - `build_informational_guardrail_instruction_fn`
- local import from `onboarding_flow`:
  - `build_first_turn_instruction`
  - `build_mixed_query_instruction`
  - `build_user_correction_instruction`
  - `build_informational_guardrail_instruction`
- pass these localized builders to `_finalize_routing_context_and_trace(...)`.

Update `bot_agent/answer_adaptive.py`:
- remove corresponding obsolete Stage-3 call args.

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
