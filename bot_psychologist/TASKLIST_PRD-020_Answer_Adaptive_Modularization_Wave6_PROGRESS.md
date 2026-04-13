# TASKLIST PRD-020: `answer_adaptive.py` Modularization (Wave 6)

## Status Legend
- [ ] pending
- [~] in progress
- [x] done

## Execution Log
- [x] Add new trace helper functions.
- [x] Wire helper usage in fast-path trace finalization.
- [x] Wire helper usage in full-path trace finalization.
- [x] Run targeted integration/regression tests.
- [x] Run full suite.
- [x] Finalize Wave 6 snapshot.

## Result Snapshot
- Added helpers in `adaptive_runtime/trace_helpers.py`:
  - `_apply_trace_model_info`
  - `_apply_trace_token_metrics`
- Replaced duplicated debug-trace enrichment in `answer_adaptive.py` with helper calls.
- Contract preserved:
  - trace model fields remain present (`primary_model`, `classifier_model`, `embedding_model`, `reranker_*`)
  - token/session metrics remain present and llm_calls fallback aggregation preserved for full-path branch.
- Validation:
  - Targeted: `13 passed`
  - Full suite: `501 passed, 13 skipped`
