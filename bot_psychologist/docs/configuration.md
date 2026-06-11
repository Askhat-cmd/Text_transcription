# Configuration (Конфигурация)

## Runtime Status (Статус runtime)
- Active runtime: `multiagent_adapter`
- Pipeline version: `multiagent_v1`
- Legacy cascade: физически удалён в PRD-041
- `answer_adaptive.py`: compatibility shim, маршрутизирующий в multiagent runtime

## Required Environment Variables (Обязательные переменные окружения)
- `OPENAI_API_KEY`: API key для model calls
- `APP_ENV`: метка runtime environment (`dev`, `stage`, `prod`)

## Core Runtime Flags (Основные runtime flags)
- `MULTIAGENT_ENABLED=true` — ожидаемое значение по умолчанию.
- `LEGACY_PIPELINE_ENABLED` — deprecated compatibility flag; не переключает runtime обратно на legacy cascade.
- Source of truth для effective runtime: `GET /api/admin/runtime/effective`.
- Source of truth для admin control Diagnostic Center:
  - `GET /api/admin/diagnostic-center/effective`
  - `POST /api/admin/diagnostic-center/control`
  - `POST /api/admin/diagnostic-center/reset`
- Boundary invariants остаются фиксированными для этой фазы:
  - `production_ready=false`
  - `broad_rollout_allowed=false`
  - `normal_user_activation_allowed=false`

## API / Web defaults (API / Web defaults)
- Локальный запуск API: `python -m uvicorn api.main:app --host 0.0.0.0 --port 8001`
- Локальный запуск Web UI: `npm run dev` в `web_ui`
- API base для web UI: `VITE_API_URL=http://localhost:8001/api/v1`

## Notes (Заметки)
- Не документируйте и не рекомендуйте `MULTIAGENT_ENABLED=false` как operational path.
- Telegram adapter существует как integration layer и не является default production channel.
