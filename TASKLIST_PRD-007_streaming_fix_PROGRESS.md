# TASKLIST PRD-007 streaming fix (progress)

Reference: `PRD-007_streaming_fix.md`

## Stage 1: Analysis and scope
- [x] Read PRD and confirm required code paths
- [x] Verify current implementation in backend/frontend
- [x] Freeze implementation checklist for this PRD

## Stage 2: Backend fixes
- [x] `bot_psychologist/bot_agent/llm_streaming.py`
- [x] `bot_psychologist/api/routes.py`

## Stage 3: Frontend fixes
- [x] `bot_psychologist/web_ui/src/services/api.service.ts`
- [x] Verify chat hook/component streaming path (no debounce/throttle regression)

## Stage 4: Tests
- [x] Update backend tests (`bot_psychologist/tests/test_llm_streaming.py`)
- [x] Update frontend tests (`bot_psychologist/web_ui/src/services/api.stream.test.ts`)
- [x] Run backend targeted tests
- [x] Run frontend targeted tests

## Stage 5: QA and closeout
- [x] Confirm no truncation/overwrite in stream contract by tests
- [x] Update this tasklist with final statuses/results

## Test results
- [x] Backend: `.\.venv\Scripts\python.exe -m pytest -q tests/test_llm_streaming.py` -> `6 passed`
- [x] Frontend: `npm run test -- src/services/api.stream.test.ts` -> `14 passed`
