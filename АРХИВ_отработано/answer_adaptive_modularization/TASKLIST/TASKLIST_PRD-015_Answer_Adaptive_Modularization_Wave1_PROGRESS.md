# TASKLIST PRD-015: `answer_adaptive.py` Modularization (Wave 1)

## Status Legend
- [ ] pending
- [~] in progress
- [x] done

## Execution Log
- [x] Create strategic master-plan document.
- [x] Create PRD-015 Wave 1 document.
- [x] Implement Wave 1 helper extraction with zero behavior drift.
- [x] Run targeted test bundle.
- [x] Run full `pytest -q tests`.
- [x] Verify entrypoint/contracts unchanged.
- [x] Finalize Wave 1 summary.

## Technical Checklist
- [x] Add package `bot_agent/adaptive_runtime`.
- [x] Add `pipeline_utils.py` and move pure helper utilities.
- [x] Add `response_utils.py (removed in Wave 142)` and move shared response helpers.
- [x] Update imports in `answer_adaptive.py`.
- [x] Remove duplicated local helper definitions from `answer_adaptive.py`.

## Validation Checklist
- [x] Adaptive endpoint tests pass.
- [x] Streaming/SSE tests pass.
- [x] Trace/contract regression tests pass.
- [x] Full suite green.

## Result Snapshot
- `answer_adaptive.py`: 3022 -> 2382 lines.
- Targeted bundle: `19 passed`.
- Full suite: `501 passed, 13 skipped`.

## Wave 1.1 Extraction (Additional)
- Added module: `bot_agent/adaptive_runtime/trace_helpers.py`.
- Moved trace/retrieval/llm-preview/session-token helper functions out of monolith.
- Kept `answer_question_adaptive` public contract intact.

