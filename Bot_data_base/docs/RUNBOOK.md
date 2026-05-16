# Runbook

## Start
```powershell
cd C:\My_practice\Text_transcription\Bot_data_base
.venv\Scripts\Activate.ps1
python -m uvicorn api.main:app --reload --port 8003
```

## Health Checks
- `GET /api/status`
- `GET /api/registry/`
- `GET /api/dashboard`
- `GET /api/dashboard/`

## Expected Runtime Snapshot
- `sources = 1`
- `focus source = 123__кузница_духа`
- `blocks = 247`
- `chroma = 247`

## Legacy SD Policy
- default: disabled
- explicit mode only: `enabled=true` + `explicit_legacy_mode=true`
- retrieval/runtime/readiness от SD не зависят
