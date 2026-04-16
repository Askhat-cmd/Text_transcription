# TASKLIST PRD-088: `answer_adaptive.py` Modularization (Wave 74)

## Status Legend
- [ ] pending
- [~] in progress
- [x] done

## Execution Log
- [x] Localize rerank gating dependencies (`feature_flags`, `should_rerank`) inside retrieval runtime helper.
- [x] Remove obsolete function-injection parameters from Stage-3 helper contracts.
- [x] Clean up call arguments in `answer_adaptive.py`.
- [x] Restore `feature_flags` compatibility touchpoint in `answer_adaptive.py` for test/runtime monkeypatch contracts.
- [x] Run expanded targeted tests.
- [x] Run full suite (`--maxfail=1`).

## Result Snapshot
- Stage-3 contract reduced by two function-injection dependencies.
- Validation:
  - Expanded targeted: `31 passed`
  - Full suite: `501 passed, 13 skipped`
