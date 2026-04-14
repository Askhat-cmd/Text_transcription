# PRD-067: `answer_adaptive.py` Modularization (Wave 53)

## Context
After Wave 52, stage-4 and full-path finalization still relied on bulky lambda-based orchestration in `answer_adaptive.py`, making maintenance and future extraction harder.

## Scope (Wave 53)
Replace lambda-heavy orchestration with dedicated high-level runtime helpers.

## Objectives
1. Remove large inline/lambda orchestration from `answer_adaptive.py`.
2. Preserve full behavior of LLM stage and full-path success stage.
3. Keep contracts for trace, validation, persistence, and metadata unchanged.

## Technical Design
Update `adaptive_runtime/runtime_misc_helpers.py`:
- add `_run_full_path_llm_stage(...)` high-level helper that orchestrates:
  - LLM generation cycle,
  - LLM error branch handling,
  - formatting/validation flow.

Update `adaptive_runtime/response_utils.py`:
- add `_run_full_path_success_stage(...)` high-level helper that orchestrates:
  - post-LLM artifacts prep,
  - full-path success response assembly.

Update `answer_adaptive.py`:
- import new runtime helpers and add compatibility wrappers,
- replace large lambda-based stage-4 and success-finalization blocks with direct helper calls.

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
