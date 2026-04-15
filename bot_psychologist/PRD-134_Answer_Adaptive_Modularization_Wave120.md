# PRD-134: `answer_adaptive.py` Modularization (Wave 120)

## Context
After Wave 119, full-path orchestration still had one remaining callable contract with `_fn` suffix:
- `build_full_path_success_response_fn`

## Scope (Wave 120)
Normalize this remaining builder dependency:
- `_run_full_path_success_stage(...)`
- callsite in `runtime_misc_helpers.py`

## Objectives
1. Remove leftover `_fn` naming artifact in full-path success flow.
2. Keep behavior and payload contracts unchanged.
3. Preserve full regression stability.

## Technical Design
### Files
- `bot_agent/adaptive_runtime/response_utils.py`
- `bot_agent/adaptive_runtime/runtime_misc_helpers.py`

### Changes
- `build_full_path_success_response_fn` -> `build_full_path_success_response`

No logic changes.

## Test Plan
Targeted:
- `tests/integration/test_generation_validation_separation.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_sparse_output_triggers_regeneration_hint.py`
- `tests/integration/test_degraded_mode_without_retrieval.py`
- `tests/test_retrieval_pipeline_simplified.py`
- `tests/regression/test_no_level_based_prompting.py`
- `tests/regression/test_trace_reflects_real_execution_only.py`

Full:
- `pytest -q`

