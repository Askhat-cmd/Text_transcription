# PRD-088: `answer_adaptive.py` Modularization (Wave 74)

## Context
Stage-3 retrieval helper contracts still accepted two function-injection dependencies (`feature_flag_enabled_fn`, `should_rerank_fn`) that are runtime internals.

## Scope (Wave 74)
Localize rerank gating dependencies inside retrieval runtime helper module.

## Objectives
1. Reduce Stage-3 helper parameter surface.
2. Keep rerank gating behavior unchanged.
3. Validate via expanded targeted and full test suites.

## Technical Design
Update `bot_agent/adaptive_runtime/retrieval_stage_helpers.py`:
- in `_prepare_conditional_rerank(...)`:
  - remove params `feature_flag_enabled_fn`, `should_rerank_fn`
  - use local imports:
    - `from ..feature_flags import feature_flags`
    - `from ..reranker_gate import should_rerank`
- remove these two params from:
  - `_run_retrieval_and_rerank_stage(...)`
  - `_run_retrieval_routing_context_stage(...)`
- update internal calls accordingly.

Update `bot_agent/answer_adaptive.py`:
- remove now-unused imports:
  - `feature_flags`
  - `should_rerank`
- remove obsolete Stage-3 arguments.

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
