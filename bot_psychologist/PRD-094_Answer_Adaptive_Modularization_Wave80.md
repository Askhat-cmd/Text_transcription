# PRD-094: `answer_adaptive.py` Modularization (Wave 80)

## Context
Stage-3 still passed several runtime-internal helper functions from `answer_adaptive.py` into retrieval orchestration.

## Scope (Wave 80)
Localize Stage-3 internal helper dependencies inside `retrieval_stage_helpers.py`:
- logging retrieval pairs
- no-retrieval fallback stage
- retrieval observability attachment
- trace preview/snapshot utilities used in routing-context finalization

## Objectives
1. Further shrink Stage-3 call contract in `answer_adaptive.py`.
2. Keep behavior and trace payloads unchanged.
3. Validate via targeted and full suites.

## Technical Design
Update `bot_agent/adaptive_runtime/retrieval_stage_helpers.py`:
- remove params from `_run_retrieval_and_rerank_stage(...)` and `_run_retrieval_routing_context_stage(...)`:
  - `log_retrieval_pairs_fn`
  - `truncate_preview_fn`
  - `refresh_context_and_apply_trace_snapshot_fn`
  - `run_no_retrieval_stage_fn`
  - `prepare_adapted_blocks_and_attach_observability_fn`
- localize imports and call directly:
  - `_log_retrieval_pairs`
  - `_run_no_retrieval_stage`
  - `_prepare_adapted_blocks_and_attach_observability`
  - `_truncate_preview`
  - `_refresh_context_and_apply_trace_snapshot`

Update `bot_agent/answer_adaptive.py`:
- remove obsolete Stage-3 arguments.
- remove now-unused import `_log_retrieval_pairs` and no-longer-needed Stage-3 helper aliases.

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
