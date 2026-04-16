# PRD-126: `answer_adaptive.py` Modularization (Wave 112)

## Context
`runtime_misc_helpers.py` still repeated the same local-import bootstrap for output validation adapter in both fast-path and full-path stages.

## Scope (Wave 112)
Centralize runtime output-validation adapter bootstrap into one shared helper.

## Objectives
1. Reduce repeated import/adapter construction logic.
2. Keep fast/full path behavior identical.
3. Maintain full regression safety.

## Technical Design
Update `bot_agent/adaptive_runtime/runtime_misc_helpers.py`:
- add `_build_runtime_output_validation_policy_adapter(force_enabled=...)`
  - localizes imports of runtime validator + policy function
  - delegates to existing `_build_output_validation_policy_adapter(...)`
- replace duplicated adapter bootstrap in:
  - `_run_fast_path_stage(...)`
  - `_run_generation_and_success_stage(...)`

No payload/contract changes.

## Test Plan
Targeted:
- `tests/integration/test_generation_validation_separation.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_sparse_output_triggers_regeneration_hint.py`
- `tests/integration/test_degraded_mode_without_retrieval.py`
- `tests/test_retrieval_pipeline_simplified.py`
- `tests/unit/test_sd_runtime_disabled.py`
- `tests/unit/test_curious_not_auto_informational.py`
- `tests/unit/test_user_level_adapter_removed.py`
- `tests/regression/test_no_level_based_prompting.py`

Full:
- `pytest -q`
