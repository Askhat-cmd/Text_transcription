# PRD-070: `answer_adaptive.py` Modularization (Wave 56)

## Context
After Wave 55, the fast-path branch in `answer_adaptive.py` remained one of the largest inline sections, combining trace bootstrap, context refresh, phase8 suffixing, fast-block generation, LLM call, validation, and success assembly.

## Scope (Wave 56)
Extract fast-path orchestration into runtime helper.

## Objectives
1. Reduce fast-path inline complexity in `answer_adaptive.py`.
2. Preserve fast-path behavior and observability contract.
3. Keep trace/metadata and token-cost accounting unchanged.

## Technical Design
Update `adaptive_runtime/runtime_misc_helpers.py`:
- add `_run_fast_path_stage(...)` orchestrator to encapsulate full fast-path pipeline.

Update `answer_adaptive.py`:
- import runtime helper alias and add wrapper,
- replace large inline `if fast_path_enabled:` branch with `_run_fast_path_stage(...)` call.

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
