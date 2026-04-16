# Release Checklist — Neo MindBot v10.1

## Runtime
- [ ] `bot_psychologist` стартует без ошибок startup validation.
- [ ] `Bot_data_base` API доступен и отвечает на retrieval-запросы.
- [ ] `/api/v1/questions/adaptive` работает в debug и non-debug режиме.

## Config safety
- [ ] Невалидный admin import не ломает runtime.
- [ ] rollback overrides возвращает предыдущую валидную конфигурацию.

## Observability
- [ ] В debug trace есть `trace_schema_valid=true`.
- [ ] В debug trace видны route/diagnostics/retrieval/practice/memory/llm blocks.
- [ ] При degraded retrieval пишется `retrieval_degraded_reason`.

## Core tests
- [ ] `python -m pytest bot_psychologist/tests/unit/test_trace_payload_schema.py -q`
- [ ] `python -m pytest bot_psychologist/tests/unit/test_config_validation.py -q`
- [ ] `python -m pytest bot_psychologist/tests/integration/test_admin_config_rollback.py -q`
- [ ] `python -m pytest bot_psychologist/tests/regression/test_partial_outage_does_not_crash_pipeline.py -q`
- [ ] `python -m pytest bot_psychologist/tests/e2e -q`

## Manual checks
- [ ] Новый пользователь (`/start`) получает мягкий onboarding.
- [ ] Informational запрос не уводится в forced coaching.
- [ ] User correction (`нет, не то`) включает recalibration protocol.
- [ ] Trace panel в UI открывается без 404 и показывает payload.

