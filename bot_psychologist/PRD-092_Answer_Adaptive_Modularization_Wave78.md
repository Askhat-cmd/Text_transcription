# PRD-092: `answer_adaptive.py` Modularization (Wave 78)

## Context
Stage-3 orchestration still injected two routing helper functions from `answer_adaptive.py` into retrieval runtime (`resolve_routing_and_apply_block_cap_fn`, `finalize_routing_context_and_trace_fn`).

## Scope (Wave 78)
Localize these routing helper dependencies inside retrieval runtime helper module.

## Objectives
1. Shrink Stage-3 function boundary by removing two helper function parameters.
2. Keep routing/block-cap/finalization behavior unchanged.
3. Validate with expanded targeted and full suites.

## Technical Design
Update `bot_agent/adaptive_runtime/retrieval_stage_helpers.py`:
- in `_run_retrieval_routing_context_stage(...)`:
  - remove params:
    - `resolve_routing_and_apply_block_cap_fn`
    - `finalize_routing_context_and_trace_fn`
  - use local imports from routing helpers:
    - `_resolve_routing_and_apply_block_cap`
    - `_finalize_routing_context_and_trace`
  - call these helpers directly.

Update `bot_agent/answer_adaptive.py`:
- remove obsolete Stage-3 call arguments for these helpers.
- remove now-unused imports from `adaptive_runtime.routing_stage_helpers`.

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
