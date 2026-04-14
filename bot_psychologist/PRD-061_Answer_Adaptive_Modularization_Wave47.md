# PRD-061: `answer_adaptive.py` Modularization (Wave 47)

## Context
Stage-3 retrieval and rerank orchestration was still inline in `answer_adaptive.py`, including degraded retrieval handling, progressive RAG dedupe/reweight, conditional rerank, and routing signal preparation.

## Scope (Wave 47)
Extract stage-3 retrieval/rerank orchestration into a dedicated runtime helper.

## Objectives
1. Reduce stage-3 inline complexity in `answer_adaptive.py`.
2. Preserve retrieval/rerank behavior and trace contract.
3. Keep downstream routing/cap logic unchanged.

## Technical Design
Update `adaptive_runtime/retrieval_stage_helpers.py`:
- add `_run_retrieval_and_rerank_stage(...)` that wraps:
  - retrieval with degraded mode,
  - progressive rag dedupe/reweight,
  - conditional rerank prep/execution/skip trace,
  - routing signal derivation.

Update `answer_adaptive.py`:
- import runtime helper alias,
- add compatibility wrapper,
- replace inline stage-3 retrieval/rerank block with helper call,
- map returned artifacts back to existing local variables.

## Test Plan
Targeted:
- `tests/test_retrieval_pipeline_simplified.py`
- `tests/integration/test_degraded_mode_without_retrieval.py`
- `tests/e2e/test_degraded_retrieval_case.py`
- `tests/integration/test_sparse_output_triggers_regeneration_hint.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`

Full:
- `pytest -q tests --maxfail=1`
