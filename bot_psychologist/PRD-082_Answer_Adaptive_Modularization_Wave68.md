# PRD-082: `answer_adaptive.py` Modularization (Wave 68)

## Context
After Wave 67, two small local wrappers remained in `answer_adaptive.py` for runtime calls with bound dependencies (`logger`, `build_working_state_fn`).

## Scope (Wave 68)
Replace these wrappers with explicit per-request local adapters to reduce top-level helper surface.

## Objectives
1. Keep `answer_adaptive.py` public/compatibility surface focused on real touchpoints.
2. Preserve behavior by binding the same dependencies at request runtime.
3. Validate no regressions across targeted and full suites.

## Technical Design
Update `answer_adaptive.py`:
- remove local wrapper defs:
  - `_build_start_command_response(...)`
  - `_set_working_state_best_effort(...)`
- add per-request local call adapters:
  - `build_start_command_response_fn = lambda **kwargs: _runtime_build_start_command_response(logger=logger, **kwargs)`
  - `set_working_state_best_effort_fn = lambda **kwargs: _runtime_set_working_state_best_effort(build_working_state_fn=_runtime_build_working_state, logger=logger, **kwargs)`
- switch all call sites to pass these local adapters.

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
