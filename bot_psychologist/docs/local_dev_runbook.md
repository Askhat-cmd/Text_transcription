# Local Dev Runbook

## Goal
Run backend and web UI locally with the current multiagent runtime contract.

## Preconditions
- Repository root: `C:\My_practice\Text_transcription`
- Python venv initialized in `bot_psychologist/.venv`
- Node dependencies installed in `bot_psychologist/web_ui`

## 1. Start backend
```powershell
cd C:\My_practice\Text_transcription\bot_psychologist
.venv\Scripts\Activate.ps1
python -m uvicorn api.main:app --host 0.0.0.0 --port 8001
```

Health check:
- `http://localhost:8001/api/v1/health`

## 2. Start web UI
```powershell
cd C:\My_practice\Text_transcription\bot_psychologist\web_ui
npm install
npm run dev
```

Open:
- `http://localhost:3000`

## 3. Runtime contract smoke
1. `GET /api/admin/runtime/effective` with `X-API-Key` returns `active_runtime=multiagent`.
2. `POST /api/v1/questions/adaptive` returns non-empty `answer`.
3. Trace endpoint `/api/debug/session/{id}/multiagent-trace` returns `200`.

## Runtime flags
- `MULTIAGENT_ENABLED` and `LEGACY_PIPELINE_ENABLED` are compatibility flags.
- Effective runtime remains multiagent-only after PRD-041/042 cutover.
- Always verify effective runtime via admin endpoint, not by assumptions from env text.
