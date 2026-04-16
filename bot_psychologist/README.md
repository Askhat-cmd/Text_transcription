# Bot Psychologist

Bot Psychologist is the active Neo MindBot runtime for reflective dialogue, retrieval-backed responses, and developer observability.

## Completion Update (2026-04-16)

`answer_adaptive.py` modularization is completed.

- Waves completed: `1-144`
- Final `answer_adaptive.py` role: facade-orchestrator only
- Final `answer_adaptive.py` size: `418` lines
- Validation baseline: `501 passed, 13 skipped`

## Architecture After Refactoring

`bot_agent/answer_adaptive.py` now orchestrates runtime stages and delegates implementation to `bot_agent/adaptive_runtime/`.

### Orchestration stages

1. Runtime bootstrap and memory preload.
2. State analysis and pre-routing.
3. Retrieval/rerank and routing context shaping.
4. Generation, output validation, and response build.
5. Memory persistence and trace finalization.

## Adaptive Runtime Modules

Полный список модулей и их назначение: [docs/architecture.md](docs/architecture.md)

## Scope

- Active workspace: `bot_psychologist/`
- Main user channel: Web chat (`web_ui`)
- Main API: `/api/v1/questions/adaptive` and `/api/v1/questions/adaptive-stream`
- Trace contract: `v2`

## Quick Start

### Backend

```powershell
cd C:\My_practice\Text_transcription\bot_psychologist
.venv\Scripts\Activate.ps1
.venv\Scripts\python.exe -m uvicorn api.main:app --host 0.0.0.0 --port 8001
```

### Frontend

```powershell
cd C:\My_practice\Text_transcription\bot_psychologist\web_ui
npm install
npm run dev
```

Web UI URL: `http://localhost:3000`
API base URL: `http://localhost:8001/api/v1`

## Core Endpoints

### Chat

- `POST /api/v1/questions/adaptive`
- `POST /api/v1/questions/adaptive-stream`

### Sessions

- `GET /api/v1/users/{user_id}/sessions`
- `POST /api/v1/users/{user_id}/sessions`
- `DELETE /api/v1/users/{user_id}/sessions/{session_id}`

### Debug

- `GET /api/debug/session/{session_id}/metrics`
- `GET /api/debug/session/{session_id}/traces`
- `GET /api/debug/session/{session_id}/llm-payload`
- `GET /api/debug/blob/{blob_id}`

## Documentation

- [Overview](docs/overview.md)
- [Architecture](docs/architecture.md)
- [Bot Agent](docs/bot_agent.md)
- [API](docs/api.md)
- [Web UI](docs/web_ui.md)
- [Testing](docs/testing.md)
- [Trace runtime](docs/trace_runtime.md)

## Notes

- `response_utils.py (removed in Wave 142)` was removed in Wave 142.
- Answer-adaptive modularization has no open TODO in active strategy.

