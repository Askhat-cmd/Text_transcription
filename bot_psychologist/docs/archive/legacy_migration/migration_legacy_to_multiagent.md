# Legacy to Multiagent Migration (Миграция: legacy cascade → multiagent runtime)

## Current Status (Текущий статус)

После PRD-036/037/039 проект работает в режиме **multiagent-only**:
- `active_runtime = multiagent`
- `runtime_entrypoint = multiagent_adapter`
- `legacy_fallback_used = false`

`answer_adaptive.py` сохранён как compatibility shim и больше не является legacy runtime entrypoint.

## Source of truth runtime (Source of truth runtime)

Проверять active runtime нужно через Admin runtime contract:
- `GET /api/admin/runtime/effective`
- `GET /api/v1/admin/runtime/effective`

Ожидаемые поля:
- `active_runtime: "multiagent"`
- `pipeline_mode: "multiagent_only"`
- `legacy.fallback_enabled: false`

## Deprecated compatibility flags

Флаги оставлены только для совместимости и не переключают runtime:
- `MULTIAGENT_ENABLED`
- `LEGACY_PIPELINE_ENABLED`
- `NEO_MINDBOT_ENABLED`

Если `LEGACY_PIPELINE_ENABLED=true`, legacy runtime всё равно не включается.

## Status After PRD-041 (Статус после PRD-041)

Legacy cascade implementation физически удалён в PRD-041.
`answer_adaptive.py` оставлен только как compatibility shim и больше не содержит legacy body.

## Status After PRD-042 (Статус после PRD-042)

PRD-042 закрыл post-purge stabilization:
- debug endpoint `/api/debug/session/{session_id}/multiagent-trace` стабилизирован fallback lookup-ом;
- при отсутствии trace endpoint возвращает явный diagnostic payload;
- добавлены regression tests на import safety, trace consistency и runtime smoke.

## Recommended Checks (Рекомендуемые проверки)

```bash
pytest tests/test_feature_flags.py -q
pytest tests/test_admin_runtime_contract.py -q
pytest tests/inventory -q
```
