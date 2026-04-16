# PRD-129: `answer_adaptive.py` Modularization (Wave 115)

## Context
In the full-path success orchestration, a subset of helper call contracts still used noisy `*_fn` parameter names even when they were already passed as concrete callable dependencies. This made signatures harder to scan and increased naming entropy across `adaptive_runtime`.

## Scope (Wave 115)
Normalize selected callable parameter names in full-path success flow:
- `_prepare_full_path_post_llm_artifacts(...)`
- `_run_full_path_success_stage(...)`
- callsite wiring in `runtime_misc_helpers.py`

## Objectives
1. Reduce signature noise in runtime orchestration.
2. Keep runtime behavior and response payloads unchanged.
3. Preserve full regression stability.

## Technical Design
### Files
- `bot_agent/adaptive_runtime/response_utils.py (removed in Wave 142)`
- `bot_agent/adaptive_runtime/runtime_misc_helpers.py`

### Changes
Rename these parameters from `*_fn` style to neutral callable contract names:
- `collect_llm_session_metrics_fn` -> `collect_llm_session_metrics`
- `update_session_token_metrics_fn` -> `update_session_token_metrics`
- `set_working_state_best_effort_fn` -> `set_working_state_best_effort`
- `build_path_recommendation_if_enabled_fn` -> `build_path_recommendation_if_enabled`
- `get_feedback_prompt_for_state_fn` -> `get_feedback_prompt_for_state`
- `persist_turn_fn` -> `persist_turn`
- `save_session_summary_best_effort_fn` -> `save_session_summary_best_effort`

No algorithm or data-contract changes.

## Test Plan
Targeted:
- `tests/integration/test_generation_validation_separation.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_sparse_output_triggers_regeneration_hint.py`
- `tests/integration/test_degraded_mode_without_retrieval.py`
- `tests/test_retrieval_pipeline_simplified.py`
- `tests/regression/test_no_level_based_prompting.py`

Full:
- `pytest -q`


