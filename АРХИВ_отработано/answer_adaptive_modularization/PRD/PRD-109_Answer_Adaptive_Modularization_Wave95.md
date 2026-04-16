# PRD-109: `answer_adaptive.py` Modularization (Wave 95)

## Context
Stage-4 still accepted facade pass-through hooks for state-context composition; output-validation policy uses a facade compatibility hook in tests and must remain passed through.

## Scope (Wave 95)
Localize state-context composition binding inside `runtime_misc_helpers.py`, removing pass-throughs from facade while preserving output-validation hook compatibility.

## Objectives
1. Reduce Stage-4 DI surface in `answer_adaptive.py` without breaking runtime monkeypatch touchpoints.
2. Keep generation/validation semantics unchanged.
3. Validate on targeted + full suites.

## Technical Design
Update `bot_agent/adaptive_runtime/runtime_misc_helpers.py`:
- narrow `_run_generation_and_success_stage(...)` signature by removing:
  - `build_state_context_fn`
  - `compose_state_context_fn`
- localize function bindings:
  - `_compose_state_context` + `_build_state_context` from `state_helpers`
- keep `apply_output_validation_policy_fn` pass-through to preserve `answer_adaptive` test/monkeypatch contract.
- wire localized state-context callables into Stage-4 internals.

Update `bot_agent/answer_adaptive.py`:
- remove obsolete Stage-4 call args for the three pass-throughs.

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
