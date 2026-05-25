# Configuration

## Runtime Status
- Active runtime: `multiagent_adapter`
- Pipeline version: `multiagent_v1`
- Legacy cascade: physically removed in PRD-041
- `answer_adaptive.py`: compatibility shim that routes into multiagent runtime

## Required Environment Variables
- `OPENAI_API_KEY`: API key for model calls
- `APP_ENV`: runtime environment label (`dev`, `stage`, `prod`)

## Core Runtime Flags
- `MULTIAGENT_ENABLED=true` is the expected default.
- `LEGACY_PIPELINE_ENABLED` is a deprecated compatibility flag and does not switch runtime back to legacy cascade.
- Source of truth for effective runtime: `GET /api/admin/runtime/effective`.
- Diagnostic Center admin control source of truth:
  - `GET /api/admin/diagnostic-center/effective`
  - `POST /api/admin/diagnostic-center/control`
  - `POST /api/admin/diagnostic-center/reset`
- Boundary invariants remain fixed for this phase:
  - `production_ready=false`
  - `broad_rollout_allowed=false`
  - `normal_user_activation_allowed=false`

## API / Web Defaults
- API local start: `python -m uvicorn api.main:app --host 0.0.0.0 --port 8001`
- Web UI local start: `npm run dev` in `web_ui`
- API base for web UI: `VITE_API_URL=http://localhost:8001/api/v1`

## Notes
- Do not document or recommend `MULTIAGENT_ENABLED=false` as an operational path.
- Telegram adapter exists as an integration layer and is not the default production channel.
