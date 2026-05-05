# Миграция: legacy cascade → multiagent runtime

## Текущий статус

После PRD-036/037/039 проект работает в режиме **multiagent-only**:
- `active_runtime = multiagent`
- `runtime_entrypoint = multiagent_adapter`
- `legacy_fallback_used = false`

`answer_adaptive.py` сохранен как compatibility shim и больше не является legacy runtime entrypoint.

## Runtime source of truth

Проверять активный runtime нужно через Admin runtime contract:
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

Если `LEGACY_PIPELINE_ENABLED=true`, legacy runtime все равно не включается.

## Статус после PRD-041

Legacy cascade implementation was physically removed in PRD-041.
`answer_adaptive.py` оставлен только как compatibility shim и больше не содержит legacy body.

## Рекомендуемые проверки

```bash
pytest tests/test_feature_flags.py -q
pytest tests/test_admin_runtime_contract.py -q
pytest tests/inventory -q
```
