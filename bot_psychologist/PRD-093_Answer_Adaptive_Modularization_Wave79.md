# PRD-093: `answer_adaptive.py` Modularization (Wave 79)

## Context
Stage-3 contract still accepted two helper functions that are stable runtime internals:
- `resolve_mode_prompt_fn`
- `build_mode_directive_fn`

## Scope (Wave 79)
Localize these dependencies inside retrieval runtime helper.

## Objectives
1. Reduce Stage-3 parameter surface by removing helper plumbing.
2. Preserve routing/block-cap behavior.
3. Validate with targeted and full test suites.

## Technical Design
Update `bot_agent/adaptive_runtime/retrieval_stage_helpers.py`:
- in `_run_retrieval_routing_context_stage(...)`:
  - remove params `resolve_mode_prompt_fn`, `build_mode_directive_fn`
  - localize imports:
    - `resolve_mode_prompt` from `mode_policy_helpers`
    - `build_mode_directive` from `decision`
  - pass localized functions into `_resolve_routing_and_apply_block_cap(...)`

Update `bot_agent/answer_adaptive.py`:
- remove obsolete Stage-3 call arguments for these functions.

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
