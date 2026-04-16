# PRD-087: `answer_adaptive.py` Modularization (Wave 73)

## Context
Stage-3 retrieval path still passed `detect_author_intent` from `answer_adaptive.py` into runtime helpers, even though this dependency is only needed inside retrieval-stage internals.

## Scope (Wave 73)
Localize author-intent dependency inside retrieval runtime helper module.

## Objectives
1. Reduce Stage-3 orchestration parameter surface.
2. Keep author-aware retrieval behavior unchanged.
3. Validate stability using targeted and full test suites.

## Technical Design
Update `bot_agent/adaptive_runtime/retrieval_stage_helpers.py`:
- in `_retrieve_blocks_with_degraded_mode(...)`:
  - remove param `detect_author_intent_fn`
  - use local import `from ..semantic_analyzer import detect_author_intent`
- remove `detect_author_intent_fn` from signatures/calls of:
  - `_run_retrieval_and_rerank_stage(...)`
  - `_run_retrieval_routing_context_stage(...)`
- cleanup unused `Callable` import.

Update `bot_agent/answer_adaptive.py`:
- remove local Stage-3 import of `detect_author_intent`.
- stop passing `detect_author_intent_fn` into Stage-3 runtime helper.

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
