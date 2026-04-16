# PRD-124: `answer_adaptive.py` Modularization (Wave 110)

## Context
`runtime_misc_helpers.py` still duplicated two internal patterns across fast-path and full-path generation flows:
1. output-validation policy adapter construction
2. `set_working_state_best_effort` adapter lambda construction

Duplication increases maintenance risk when contracts evolve.

## Scope (Wave 110)
Internal dedup in `runtime_misc_helpers.py` only, without behavior changes.

## Objectives
1. Remove duplicated adapter boilerplate.
2. Keep fast-path and full-path behavior strictly equivalent.
3. Preserve monkeypatch/test contracts and keep full suite green.

## Technical Design
Update `bot_agent/adaptive_runtime/runtime_misc_helpers.py`:
- add `_build_output_validation_policy_adapter(...)`
- add `_build_set_working_state_best_effort_adapter(...)`
- replace duplicated inline adapter/lambda code in:
  - `_run_fast_path_stage(...)`
  - `_run_generation_and_success_stage(...)`

No API/schema/trace contract changes.

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
