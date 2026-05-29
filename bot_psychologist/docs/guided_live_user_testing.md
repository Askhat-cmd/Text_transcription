# Guided Live User Testing (PRD-047.7)

## Purpose
This protocol gives project owner a structured developer-local workflow for live dialogue testing, feedback capture, and evidence handoff to next PRD.

## Start Backend and Frontend
1. Backend (example):
```powershell
cd C:\My_practice\Text_transcription\bot_psychologist
python -m uvicorn api.main:app --host 127.0.0.1 --port 8015
```
2. Frontend:
```powershell
cd C:\My_practice\Text_transcription\bot_psychologist\web_ui
npm run dev
```
3. Open Web UI and run normal dialogue.

## Scenario Set
Use:
- `bot_psychologist/tests/evaluation/prd_047_7_guided_live_scenarios.json`

Categories:
- ordinary understanding
- low resource
- soft distress
- practice boundary
- defensive I+W-
- known concept / KB
- close / continuation

## How To Test
1. Pick one scenario prompt.
2. Talk naturally, not in synthetic QA style.
3. After each answer capture feedback with CLI:
```powershell
cd C:\My_practice\Text_transcription\bot_psychologist
python scripts/live_feedback_capture.py --session-id live_test_001 --turn-id turn_01 --scenario-id gl_001_stuck_start --rating 4 --felt-alive true --felt-understood true --felt-too-rigid false --felt-too-generic false --too-many-questions false --too-much-practice false --comment "Ответ попал, можно теплее" --user-message-preview "Я зависаю перед стартом" --answer-preview "Короткий ответ бота..."
```

## What To Evaluate
For each turn capture:
- liveliness
- understood feeling
- rigidity
- genericity
- too long / too short
- too many questions
- too much practice
- missed context
- safety concern
- free comment

## Build Session Summary
After session:
```powershell
cd C:\My_practice\Text_transcription\bot_psychologist
python scripts/build_live_feedback_summary.py --session-id live_test_001
```
Artifacts:
- `TO_DO_LIST/live_feedback/PRD-047.7/reports/live_test_001_summary.json`
- `TO_DO_LIST/live_feedback/PRD-047.7/reports/live_test_001_summary.md`

## Smoke Validation
Dry smoke:
```powershell
python scripts/run_prd_047_7_guided_live_feedback_smoke.py --mode dry
```
Optional live smoke (backend available):
```powershell
python scripts/run_prd_047_7_guided_live_feedback_smoke.py --mode live --api-base-url http://127.0.0.1:8015/api/v1 --admin-runtime-url http://127.0.0.1:8015/api/admin/runtime/effective
```

## Privacy and Boundaries
- feedback storage is sanitized file summary
- raw private full dialogue is not saved by default
- no raw provider payload
- no secrets/.env in artifacts
- feedback does not auto-mutate runtime behavior
- no answer blocking and no final answer rewrite

## PRD-047.9 Note
- For MVP context-unclamp acceptance, use:
```powershell
python scripts/run_prd_047_9_mvp_context_unclamp_cases.py --mode live --api-base-url http://127.0.0.1:8016/api/v1 --admin-runtime-url http://127.0.0.1:8016/api/admin/runtime/effective
```
- Live acceptance must be `passed` (not `blocked`) on a fresh backend process.
