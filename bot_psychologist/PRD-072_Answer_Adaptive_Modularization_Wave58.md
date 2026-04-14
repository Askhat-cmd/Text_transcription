# PRD-072: `answer_adaptive.py` Modularization (Wave 58)

## Context
After Wave 57, `answer_adaptive.py` still contained compatibility wrappers/import aliases that were no longer referenced by runtime flow.

## Scope (Wave 58)
Remove dead wrappers/import aliases that were superseded by extracted runtime helpers in previous waves.

## Objectives
1. Reduce facade noise in `answer_adaptive.py`.
2. Keep runtime behavior unchanged.
3. Improve readability and lower accidental maintenance overhead.

## Technical Design
Update `answer_adaptive.py`:
- remove unused alias imports:
  - `_runtime_prepare_full_path_post_llm_artifacts`
  - `_runtime_handle_no_retrieval_partial_response`
  - `_runtime_attach_retrieval_observability`
  - `_runtime_resolve_practice_selection_context`
  - `_runtime_attach_routing_stage_debug_trace`
- remove unused compatibility wrappers:
  - `_prepare_full_path_post_llm_artifacts(...)`
  - `_handle_no_retrieval_partial_response(...)`
  - `_attach_retrieval_observability(...)`
  - `_resolve_practice_selection_context(...)`
  - `_attach_routing_stage_debug_trace(...)`

## Test Plan
Targeted:
- `tests/test_retrieval_pipeline_simplified.py`
- `tests/integration/test_degraded_mode_without_retrieval.py`
- `tests/e2e/test_degraded_retrieval_case.py`
- `tests/integration/test_sparse_output_triggers_regeneration_hint.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_routing_recalibration_for_exploratory_queries.py`
- `tests/integration/test_adaptive_stream_contract.py`
- `tests/test_sse_payload.py`

Full:
- `pytest -q tests --maxfail=1`
