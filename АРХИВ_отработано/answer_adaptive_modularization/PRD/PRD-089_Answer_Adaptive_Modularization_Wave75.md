# PRD-089: `answer_adaptive.py` Modularization (Wave 75)

## Context
Stage-3 retrieval flow still passed `get_progressive_rag_fn` from `answer_adaptive.py`, while progressive-rag loading is an internal retrieval concern.

## Scope (Wave 75)
Localize progressive-rag loader dependency inside retrieval runtime helper module.

## Objectives
1. Reduce Stage-3 parameter surface by one dependency.
2. Preserve retrieval + progressive feedback behavior.
3. Validate with targeted and full test suites.

## Technical Design
Update `bot_agent/adaptive_runtime/retrieval_stage_helpers.py`:
- in `_run_retrieval_and_rerank_stage(...)`:
  - remove param `get_progressive_rag_fn`
  - use local import `from ..progressive_rag import get_progressive_rag`
- in `_run_retrieval_routing_context_stage(...)`:
  - remove param `get_progressive_rag_fn`
  - update internal call accordingly.

Update `bot_agent/answer_adaptive.py`:
- remove import `get_progressive_rag`.
- remove obsolete Stage-3 call argument.

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
