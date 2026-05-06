# Testing Matrix

## Goal

Минимальный обязательный набор проверок перед merge для multiagent-only runtime.

## Core runtime checks

```bash
pytest tests/test_feature_flags.py -q
pytest tests/test_admin_runtime_contract.py -q
pytest tests/inventory/test_post_purge_no_broken_legacy_imports.py -q
pytest tests/api/test_multiagent_trace_storage_consistency.py -q
pytest tests/e2e/test_post_purge_runtime_smoke.py -q
pytest tests/inventory -q
pytest tests/api -q
pytest tests/multiagent -q
```

Expected:
- `active_runtime=multiagent` в admin runtime contract
- `legacy.fallback_enabled=false`
- `legacy.cascade_status=physically_removed`
- отсутствуют legacy runtime mode переключатели
- `bot_agent/adaptive_runtime/` отсутствует (PRD-041 physical purge)
- `answer_adaptive.py` не содержит legacy cascade body
- `/api/debug/session/{id}/multiagent-trace` стабилен (200 на доступный trace или диагностический 404 payload)

## Telegram/registration package

```bash
pytest tests/registration tests/telegram_adapter -q
```

## Runtime contract smoke

1. `GET /api/admin/runtime/effective` returns `active_runtime: "multiagent"`.
2. `pipeline_mode` is `multiagent_only`.
3. `deprecated_runtime_flags` includes `MULTIAGENT_ENABLED` and `LEGACY_PIPELINE_ENABLED`.
4. If `LEGACY_PIPELINE_ENABLED=true`, runtime still stays multiagent.
5. `tests/inventory/test_physical_legacy_purge.py` passes.
6. `tests/api/test_multiagent_trace_storage_consistency.py` passes.

## PASS criteria

- Все команды выше green.
- Нет regressions в runtime contract и multiagent тестах.
