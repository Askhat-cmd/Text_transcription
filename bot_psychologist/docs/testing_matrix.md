# Testing Matrix

## Goal

Минимальный обязательный набор проверок перед merge для multiagent-only runtime.

## Core runtime checks

```bash
pytest tests/test_feature_flags.py -q
pytest tests/test_admin_runtime_contract.py -q
pytest tests/inventory -q
pytest tests/api -q
pytest tests/multiagent -q
```

Expected:
- `active_runtime=multiagent` в admin runtime contract
- `legacy.fallback_enabled=false`
- отсутствуют legacy runtime mode переключатели

## Telegram/registration package

```bash
pytest tests/registration tests/telegram_adapter -q
```

## Runtime contract smoke

1. `GET /api/admin/runtime/effective` returns `active_runtime: "multiagent"`.
2. `pipeline_mode` is `multiagent_only`.
3. `deprecated_runtime_flags` includes `MULTIAGENT_ENABLED` and `LEGACY_PIPELINE_ENABLED`.
4. If `LEGACY_PIPELINE_ENABLED=true`, runtime still stays multiagent.

## PASS criteria

- Все команды выше green.
- Нет regressions в runtime contract и multiagent тестах.
