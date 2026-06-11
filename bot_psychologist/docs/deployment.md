# Deployment (Развёртывание)

## Scope (Область)
Заметки по развёртыванию для текущей multiagent runtime architecture.

## Runtime baseline (Базовый runtime)
- Active runtime: `multiagent_adapter`
- Legacy cascade: удалён в PRD-041
- Post-purge stabilization: завершена в PRD-042

## Recommended production controls (Рекомендуемые production controls)
1. Guardrails `APP_ENV=prod` и явная config validation.
2. Strict CORS allowlist.
3. Centralized rate limiting (shared store, например Redis).
4. Structured logs и trace-safe export policy.

## Health и contract checks (Health и contract checks)
- `GET /api/v1/health`
- `GET /api/admin/runtime/effective`
- Multiagent trace endpoint возвращает consistent runtime metadata.

## Rollout checklist (Чеклист rollout)
1. Применить environment configuration и secrets.
2. Запустить API с process manager.
3. Собрать и отдавать web UI artifacts.
4. Запустить inventory + core backend regression tests перед promotion.

## Out of scope for this doc (Вне scope этого документа)
- Повторное включение legacy cascade runtime.
- Production activation Telegram channel по умолчанию.
