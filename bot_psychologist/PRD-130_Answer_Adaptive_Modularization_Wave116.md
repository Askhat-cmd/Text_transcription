# PRD-130: `answer_adaptive.py` Modularization (Wave 116)

## Context
After Wave 115, fast-path success orchestration still exposed several `*_fn` callable contracts with unnecessary suffix noise, while behavior already depended on concrete injected callables.

## Scope (Wave 116)
Normalize selected callable parameter names in fast-path success builder:
- `_build_fast_path_success_response(...)`
- callsite wiring in `runtime_misc_helpers.py`

## Objectives
1. Continue contract readability alignment across runtime helpers.
2. Keep fast-path behavior and response schema unchanged.
3. Preserve full regression stability.

## Technical Design
### Files
- `bot_agent/adaptive_runtime/response_utils.py`
- `bot_agent/adaptive_runtime/runtime_misc_helpers.py`

### Changes
Rename selected parameters:
- `collect_llm_session_metrics_fn` -> `collect_llm_session_metrics`
- `update_session_token_metrics_fn` -> `update_session_token_metrics`
- `persist_turn_fn` -> `persist_turn`
- `get_feedback_prompt_for_state_fn` -> `get_feedback_prompt_for_state`
- `build_success_response_fn` -> `build_success_response`
- `build_fast_success_metadata_fn` -> `build_fast_success_metadata`

No behavior changes; only contract naming cleanup.

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

