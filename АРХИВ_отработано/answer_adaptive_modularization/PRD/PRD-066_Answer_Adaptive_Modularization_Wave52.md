# PRD-066: `answer_adaptive.py` Modularization (Wave 52)

## Context
After Wave 51, full-path finalization in `answer_adaptive.py` still contained a large inline block that orchestrated post-LLM artifact preparation and success response assembly.

## Scope (Wave 52)
Extract full-path finalization orchestration into response runtime helper.

## Objectives
1. Reduce end-of-pipeline inline complexity in `answer_adaptive.py`.
2. Preserve post-LLM artifact contract and success metadata integrity.
3. Keep full-path success response behavior unchanged.

## Technical Design
Update `adaptive_runtime/response_utils.py (removed in Wave 142)`:
- add `_finalize_full_path_success_stage(...)` orchestrator to map post-LLM artifacts into success response builder.

Update `answer_adaptive.py`:
- import runtime helper alias and add compatibility wrapper,
- replace inline post-LLM finalization block with helper call.

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

