# PRD-090: `answer_adaptive.py` Modularization (Wave 76)

## Context
Stage-3 retrieval runtime contracts still passed `timed_fn` from `answer_adaptive.py`, although timing is a shared runtime utility and can be owned inside retrieval helpers.

## Scope (Wave 76)
Localize timing utility usage for retrieval/rerank stages.

## Objectives
1. Reduce Stage-3 contract surface by removing `timed_fn` plumbing.
2. Keep stage timing and trace metrics behavior unchanged.
3. Validate with expanded targeted and full test suites.

## Technical Design
Update `bot_agent/adaptive_runtime/retrieval_stage_helpers.py`:
- import runtime timer locally from pipeline utils:
  - `from .pipeline_utils import _timed as _runtime_timed`
- remove `timed_fn` parameter from:
  - `_retrieve_blocks_with_degraded_mode(...)`
  - `_run_retrieval_and_rerank_stage(...)`
  - `_run_retrieval_routing_context_stage(...)`
- replace timing calls with `_runtime_timed(...)`.

Update `bot_agent/answer_adaptive.py`:
- remove obsolete `timed_fn` argument in Stage-3 call.

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
