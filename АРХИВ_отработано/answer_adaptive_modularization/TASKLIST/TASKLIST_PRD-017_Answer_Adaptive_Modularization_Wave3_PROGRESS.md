# TASKLIST PRD-017: `answer_adaptive.py` Modularization (Wave 3)

## Status Legend
- [ ] pending
- [~] in progress
- [x] done

## Execution Log
- [x] Create PRD-017 Wave 3 document.
- [x] Extract state-context + working-state helpers.
- [x] Replace local helper implementations with proxies.
- [x] Run targeted test bundle.
- [x] Run full `pytest -q tests`.
- [x] Finalize Wave 3 snapshot.

## Technical Checklist
- [x] Extend `adaptive_runtime/state_helpers.py` with context/working-state functions.
- [x] Keep function behavior byte-compatible from caller perspective.
- [x] Keep contracts of `answer_question_adaptive` untouched.

## Validation Checklist
- [x] Targeted adaptive/streaming tests pass.
- [x] Full suite green.

## Result Snapshot
- `answer_adaptive.py`: 2188 -> 2146 lines.
- `adaptive_runtime/state_helpers.py`: 120 -> 201 lines.
- Targeted bundle: `13 passed`.
- Full suite: `501 passed, 13 skipped`.
