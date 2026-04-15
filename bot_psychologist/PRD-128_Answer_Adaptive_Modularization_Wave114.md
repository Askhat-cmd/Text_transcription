# PRD-128: `answer_adaptive.py` Modularization (Wave 114)

## Context
`runtime_misc_helpers.py` still had a dead helper `_sd_runtime_disabled()` with no active callsites.

## Scope (Wave 114)
Remove dead `_sd_runtime_disabled()` helper.

## Objectives
1. Reduce dead code in active runtime helper module.
2. Keep SD-disabled runtime behavior unchanged.
3. Preserve full regression stability.

## Technical Design
Update `bot_agent/adaptive_runtime/runtime_misc_helpers.py`:
- delete unused function `_sd_runtime_disabled()`.

No runtime behavior/API/trace changes.

## Test Plan
Targeted:
- `tests/unit/test_sd_runtime_disabled.py`
- `tests/unit/test_sd_legacy_final_cleanup_prompt_context.py`
- `tests/regression/test_trace_reflects_real_execution_only.py`
- `tests/integration/test_generation_validation_separation.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_sparse_output_triggers_regeneration_hint.py`
- `tests/integration/test_degraded_mode_without_retrieval.py`
- `tests/test_retrieval_pipeline_simplified.py`
- `tests/regression/test_no_level_based_prompting.py`

Full:
- `pytest -q`
