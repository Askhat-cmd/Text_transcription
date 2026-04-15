# PRD-125: `answer_adaptive.py` Modularization (Wave 111)

## Context
After Wave 109 extraction, startup context helper still used callback-style naming:
- `output_validation_enabled_fn`

To keep contracts readable and consistent, this should use a neutral dependency name.

## Scope (Wave 111)
Rename the startup helper dependency from callback-style name to neutral reader name.

## Objectives
1. Improve contract readability.
2. Keep behavior unchanged and tests green.
3. Continue reducing callback-style naming noise.

## Technical Design
Update:
- `bot_agent/adaptive_runtime/runtime_misc_helpers.py`
  - `_prepare_adaptive_run_context(...): output_validation_enabled_fn -> output_validation_enabled_reader`
- `bot_agent/answer_adaptive.py`
  - update callsite keyword accordingly.

No behavior changes.

## Test Plan
Targeted:
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_generation_validation_separation.py`
- `tests/integration/test_sparse_output_triggers_regeneration_hint.py`
- `tests/integration/test_degraded_mode_without_retrieval.py`
- `tests/test_retrieval_pipeline_simplified.py`
- `tests/unit/test_sd_runtime_disabled.py`
- `tests/unit/test_curious_not_auto_informational.py`
- `tests/unit/test_user_level_adapter_removed.py`
- `tests/regression/test_no_level_based_prompting.py`

Full:
- `pytest -q`
