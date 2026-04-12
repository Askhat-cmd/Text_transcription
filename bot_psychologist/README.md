# Bot Psychologist

Bot Psychologist is a Neo MindBot runtime for reflective dialogue, context-aware retrieval, and full developer observability in Web UI.

## Scope

- Active workspace: `bot_psychologist/`
- Main user channel: Web chat (`web_ui`)
- Main API: adaptive flow (`/api/v1/questions/adaptive` and `/api/v1/questions/adaptive-stream`)
- Trace contract: `v2`

## Runtime Snapshot

The current runtime is built around one production path:

1. Route and state detection.
2. Retrieval and optional rerank.
3. Prompt stack build.
4. LLM call.
5. Output validation and formatting.
6. Memory update.
7. Trace export for diagnostics.

This keeps one runtime truth for non-stream and SSE responses.

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

Web UI default URL: `http://localhost:3000`
API base URL: `http://localhost:8001/api/v1`

## Core Endpoints

### Chat

- `POST /api/v1/questions/adaptive`
- `POST /api/v1/questions/adaptive-stream`

### Sessions

- `GET /api/v1/users/{user_id}/sessions`
- `POST /api/v1/users/{user_id}/sessions`
- `DELETE /api/v1/users/{user_id}/sessions/{session_id}`

### Debug (developer access)

- `GET /api/debug/session/{session_id}/metrics`
- `GET /api/debug/session/{session_id}/traces`
- `GET /api/debug/session/{session_id}/llm-payload`
- `GET /api/debug/blob/{blob_id}`

## Trace v2 (Web Inline Debug)

Trace in Web UI is Neo-only and follows `trace_contract_version = "v2"`.

### Status chips

- `MODE`
- `STATE`
- `RULE`
- `CHUNKS`
- `HITS`
- `TOKENS`
- `LLM`
- `WARN`

### Deep sections

- Routing and state
- Pipeline timeline
- Retrieval chunks
- LLM calls
- Memory context
- Models / tokens / cost
- Anomalies
- Session dashboard
- Trace history
- Config snapshot
- LLM canvas (developer key only, collapsed by default)

## Configuration

Use `.env` based on `.env.example`.

Most important switches for local development:

- `NEO_MINDBOT_ENABLED=true`
- `LEGACY_PIPELINE_ENABLED=false`
- `USE_NEW_DIAGNOSTICS_V1=true`
- `USE_DETERMINISTIC_ROUTE_RESOLVER=true`
- `USE_PROMPT_STACK_V2=true`
- `USE_OUTPUT_VALIDATION=true`
- `ENABLE_STREAMING=true`
- `LLM_PAYLOAD_INCLUDE_FULL_CONTENT=true`

## Tests

Run from `bot_psychologist/`.

```powershell
pytest -q
```

Targeted checks used for runtime and trace:

```powershell
pytest tests/contract tests/ui tests/inventory tests/regression tests/test_llm_payload_endpoint.py tests/test_sse_payload.py -q
```

## Project Layout

```text
bot_psychologist/
  api/                 FastAPI routes, schemas, debug endpoints
  bot_agent/           Runtime orchestration, prompts, retrieval, memory
  config/              Feature flags and configuration
  data/                Runtime data and admin overrides
  docs/                Technical docs
  logs/                Runtime logs
  migrations/          Data migration helpers
  scripts/             Maintenance and evaluation scripts
  tests/               Unit, integration, contract, UI, regression tests
  web_ui/              React Web chat and admin UI
```

## Documentation

- [Overview](docs/overview.md)
- [Architecture](docs/architecture.md)
- [Bot Agent](docs/bot_agent.md)
- [API](docs/api.md)
- [Web UI](docs/web_ui.md)
- [Testing](docs/testing.md)
- [Runtime notes](docs/neo_runtime_v101.md)

## Current cleanup program

- Runtime audit report in project root.
- PRD-012 implementation pack in project root.
- Progress tasklist in project root.
