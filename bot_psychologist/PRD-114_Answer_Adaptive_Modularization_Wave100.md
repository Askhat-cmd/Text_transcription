# PRD-114: `answer_adaptive.py` Modularization (Wave 100)

## Context
Facade still passed output-validation callback into runtime stages, although this policy is runtime-stable and can be localized in helper layer.

## Scope (Wave 100)
Localize output-validation policy wiring inside `runtime_misc_helpers.py` and remove obsolete callback pass-through from `answer_adaptive.py`.

## Objectives
1. Narrow facade contracts for fast-path and full-path stage calls.
2. Preserve output-validation behavior and test monkeypatch contracts.
3. Keep full regression suite green.

## Technical Design
Update `bot_agent/adaptive_runtime/runtime_misc_helpers.py`:
- remove stage args:
  - `_run_fast_path_stage(...): apply_output_validation_policy_fn`
  - `_run_generation_and_success_stage(...): apply_output_validation_policy_fn`
- localize validator wiring:
  - import `output_validator` and `_apply_output_validation_policy` in helper
  - use local adapter with `force_enabled=output_validation_enabled` to preserve runtime toggle behavior expected by tests.

Update `bot_agent/answer_adaptive.py`:
- remove obsolete call args:
  - `apply_output_validation_policy_fn=_apply_output_validation_policy` from fast-path stage call
  - `apply_output_validation_policy_fn=_apply_output_validation_policy` from full-path stage call

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
