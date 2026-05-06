# Web UI

## Purpose
React application for chat, diagnostics, and admin-adjacent operator workflows over REST API.

## Current contract alignment
- Backend API is multiagent-only at runtime.
- Trace widgets consume multiagent trace payloads.
- UI should not display legacy cascade as an active runtime option.

## Local start
```powershell
cd C:\My_practice\Text_transcription\bot_psychologist\web_ui
npm install
npm run dev
```

Default local URL:
- `http://localhost:3000`

## Build
```powershell
npm run build
```

## Required env
- `VITE_API_URL` (example: `http://localhost:8001/api/v1`)
- `VITE_API_KEY` (dev/test key)

## Minimal UI smoke
1. Open chat page and send one message.
2. Verify response is non-empty.
3. Open trace panel and confirm writer model metadata is visible.
4. Confirm runtime badge indicates multiagent runtime.
