# Guided Live User Testing PRD-047.7 (Guided Live User Testing, PRD-047.7)

## Purpose (Назначение)
Протокол даёт project owner структурированный developer-local workflow для live dialogue testing, feedback capture и передачи evidence в следующий PRD.

## Start Backend and Frontend (Запуск backend и frontend)
1. Backend (пример):
```powershell
cd C:\My_practice\Text_transcription\bot_psychologist
python -m uvicorn api.main:app --host 127.0.0.1 --port 8015
```
2. Frontend:
```powershell
cd C:\My_practice\Text_transcription\bot_psychologist\web_ui
npm run dev
```
3. Откройте Web UI и ведите обычный диалог.

## Scenario Set (Набор сценариев)
Используйте:
- `bot_psychologist/tests/evaluation/prd_047_7_guided_live_scenarios.json`

Категории:
- ordinary understanding
- low resource
- soft distress
- practice boundary
- defensive I+W-
- known concept / KB
- close / continuation

## How To Test (Как тестировать)
1. Выберите один scenario prompt.
2. Говорите естественно, не в synthetic QA style.
3. После каждого answer захватите feedback через CLI:
```powershell
cd C:\My_practice\Text_transcription\bot_psychologist
python scripts/live_feedback_capture.py --session-id live_test_001 --turn-id turn_01 --scenario-id gl_001_stuck_start --rating 4 --felt-alive true --felt-understood true --felt-too-rigid false --felt-too-generic false --too-many-questions false --too-much-practice false --comment "Ответ попал, можно теплее" --user-message-preview "Я зависаю перед стартом" --answer-preview "Короткий ответ бота..."
```

## What To Evaluate (Что оценивать)
На каждый turn захватывайте:
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

## Build Session Summary (Сборка session summary)
После session:
```powershell
cd C:\My_practice\Text_transcription\bot_psychologist
python scripts/build_live_feedback_summary.py --session-id live_test_001
```
Артефакты:
- `TO_DO_LIST/live_feedback/PRD-047.7/reports/live_test_001_summary.json`
- `TO_DO_LIST/live_feedback/PRD-047.7/reports/live_test_001_summary.md`

## Smoke validation (Smoke validation)
Dry smoke:
```powershell
python scripts/run_prd_047_7_guided_live_feedback_smoke.py --mode dry
```
Optional live smoke (backend доступен):
```powershell
python scripts/run_prd_047_7_guided_live_feedback_smoke.py --mode live --api-base-url http://127.0.0.1:8015/api/v1 --admin-runtime-url http://127.0.0.1:8015/api/admin/runtime/effective
```

## Privacy and Boundaries (Privacy и границы)
- feedback storage — sanitized file summary
- raw private full dialogue по умолчанию не сохраняется
- без raw provider payload
- без secrets/.env в artifacts
- feedback не auto-mutate runtime behavior
- без answer blocking и без final answer rewrite

## PRD-047.9 Note (Заметка PRD-047.9)
- Для MVP context-unclamp acceptance используйте:
```powershell
python scripts/run_prd_047_9_mvp_context_unclamp_cases.py --mode live --api-base-url http://127.0.0.1:8016/api/v1 --admin-runtime-url http://127.0.0.1:8016/api/admin/runtime/effective
```
- Live acceptance должен быть `passed` (не `blocked`) на fresh backend process.
