# Local Dev Runbook (Runbook локальной разработки)

## Goal (Цель)
Запустить backend и web UI локально с текущим multiagent runtime contract.

## Preconditions (Предусловия)
- Корень репозитория: `C:\My_practice\Text_transcription`
- Python venv инициализирован в `bot_psychologist/.venv`
- Node dependencies установлены в `bot_psychologist/web_ui`

## Start backend (Запуск backend)
```powershell
cd C:\My_practice\Text_transcription\bot_psychologist
.venv\Scripts\Activate.ps1
python -m uvicorn api.main:app --host 0.0.0.0 --port 8001
```

Health check:
- `http://localhost:8001/api/v1/health`

## Start web UI (Запуск web UI)
```powershell
cd C:\My_practice\Text_transcription\bot_psychologist\web_ui
npm install
npm run dev
```

Открыть:
- `http://localhost:3000`

## 3. Smoke runtime contract (Smoke runtime contract)
1. `GET /api/admin/runtime/effective` с `X-API-Key` возвращает `active_runtime=multiagent`.
2. `POST /api/v1/questions/adaptive` возвращает непустой `answer`.
3. Trace endpoint `/api/debug/session/{id}/multiagent-trace` возвращает `200`.

## Runtime flags (флаги runtime)
- `MULTIAGENT_ENABLED` и `LEGACY_PIPELINE_ENABLED` — compatibility flags.
- Effective runtime остаётся multiagent-only после cutover PRD-041/042.
- Всегда проверяйте effective runtime через admin endpoint, а не по предположениям из env text.
