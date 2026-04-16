# PRD-084: `answer_adaptive.py` Modularization (Wave 70)

## Context
After Wave 69, Stage-3 path still proxied trace debug-builder helpers from `answer_adaptive.py` into retrieval/runtime layers, despite these helpers being native to `adaptive_runtime.trace_helpers`.

## Scope (Wave 70)
Collapse debug observability helper plumbing by using trace-local helpers directly.

## Objectives
1. Reduce argument surface across Stage-3 and trace observability calls.
2. Keep retrieval/trace payload behavior unchanged.
3. Validate against targeted + full test suites.

## Technical Design
Update `bot_agent/adaptive_runtime/trace_helpers.py`:
- simplify `_attach_retrieval_observability(...)` by removing function-injection params and calling:
  - `_build_retrieval_debug_details(...)`
  - `_build_retrieval_detail(...)`
  - `_build_voyage_rerank_debug_payload(...)`
  - `_build_routing_debug_payload(...)`
  - `_build_chunk_trace_lists_after_rerank(...)`
- simplify `_prepare_adapted_blocks_and_attach_observability(...)` signature accordingly.

Update `bot_agent/adaptive_runtime/retrieval_stage_helpers.py`:
- remove now-obsolete Stage-3 params:
  - `build_retrieval_debug_details_fn`
  - `build_retrieval_detail_fn`
  - `build_voyage_rerank_debug_payload_fn`
  - `build_routing_debug_payload_fn`
  - `build_chunk_trace_lists_after_rerank_fn`
- call `_prepare_adapted_blocks_and_attach_observability(...)` with compact args.

Update `bot_agent/answer_adaptive.py`:
- remove now-unused trace helper imports.
- remove obsolete Stage-3 call arguments.

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
