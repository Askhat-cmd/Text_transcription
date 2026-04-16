# PRD-127: `answer_adaptive.py` Modularization (Wave 113)

## Context
`runtime_misc_helpers.py` contained an orphan helper `_execute_full_path_llm_stage(...)` that was no longer referenced by active runtime path or tests.

## Scope (Wave 113)
Remove dead helper from runtime misc module.

## Objectives
1. Reduce dead code surface.
2. Keep runtime behavior unchanged.
3. Preserve full regression stability.

## Technical Design
Update `bot_agent/adaptive_runtime/runtime_misc_helpers.py`:
- delete unused function `_execute_full_path_llm_stage(...)`

No API/trace/schema contract changes.

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
