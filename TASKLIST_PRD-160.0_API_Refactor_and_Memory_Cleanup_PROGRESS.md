# TASKLIST PRD-160.0 — Рефакторинг API-слоя и очистка памяти

Статус: done  
Дата старта: 2026-04-17
Дата завершения: 2026-04-25

## Волна 1 — memory_v11 cleanup
- [x] Проверить отсутствие импортов `memory_v11` по проекту
- [x] Удалить `bot_psychologist/bot_agent/memory_v11.py` (после миграции runtime и тестов)
- [x] Обновить `bot_psychologist/README.md` (секция «Память»)
- [x] Проверка: `rg -n "memory_v11" bot_psychologist`

## Волна 8 — migration runtime memory context
- [x] Добавлен `bot_psychologist/bot_agent/memory_context.py` (контекст памяти и staleness policy)
- [x] Runtime переведен на `memory_context` (`memory_updater.py`, `summary_manager.py`)
- [x] Удалены legacy-fallback на v11 в trace (`adaptive_runtime/trace_helpers.py`)
- [x] Перенесены memory-тесты и контракты на v12 (`test_memory_contract_v12.py`, `test_snapshot_schema_v12.py`)

## Волна 2 — маршрутизация API: каркас package
- [x] Создать `bot_psychologist/api/routes/`
- [x] Создать `__init__.py` с объединением sub-router
- [x] Добавить `chat.py`, `users.py`, `feedback.py`, `health.py`
- [x] Проверка импорта: `python -c "from api.routes import router; print('OK')"`

## Волна 3 — перенос small endpoints
- [x] Перенести health/stats endpoint в `health.py`
- [x] Перенести feedback endpoint в `feedback.py`
- [x] Проверка импорта: `python -c "from api.routes import router; print('OK')"`

## Волна 4 — перенос users endpoints
- [x] Перенести `/users/*`, `/sessions/archive` в `users.py`
- [x] Сохранить текущие response-модели и поведение
- [x] Проверка импорта: `python -c "from api.routes import router; print('OK')"`

## Волна 5 — перенос chat endpoints
- [x] Перенести `/questions/*` в `chat.py`
- [x] Сохранить streaming и trace-логику без функциональных изменений
- [x] Проверка импорта: `python -c "from api.routes import router; print('OK')"`

## Волна 6 — финализация package
- [x] Удалить legacy `bot_psychologist/api/routes.py`
- [x] Проверить, что `api/main.py` не изменялся
- [x] Проверка импорта: `python -c "from api.routes import router; print('OK')"`
- [x] Восстановить public-экспорты `api.routes` для тест-контрактов (`ask_adaptive_question`, `ask_adaptive_question_stream`, `health_check`, `_build_turn_diff`)

## Волна 7 — README prod CORS note
- [x] Добавить предупреждение про `allow_origins=["*"]` только для local dev
- [x] Проверка: `rg -n "allow_origins|внешний сервер|CORS" bot_psychologist/README.md`

## Волна 9 — совместимость API контрактов после split `api.routes`
- [x] Восстановлен monkeypatch-контракт для `routes.answer_question_adaptive`
- [x] Добавлен monkeypatch-контракт для `routes.stream_answer_tokens`
- [x] Обновлены inventory/contract тесты на новый пакетный layout (`api/routes/chat.py`, `api/routes/common.py`)
- [x] Исправлен missing import в `api/routes/users.py` (`ConversationTurnResponse`, `datetime`)

## Тесты и проверки
- [x] Smoke import: `python -c "from api.routes import router; print('OK')"`
- [x] Базовая компиляция API: `python -m py_compile bot_psychologist/api/main.py`
- [x] Targeted sanity:
  - [x] `python -m py_compile bot_psychologist/api/routes/chat.py`
  - [x] `python -m py_compile bot_psychologist/api/routes/users.py`
  - [x] `python -m py_compile bot_psychologist/api/routes/feedback.py`
  - [x] `python -m py_compile bot_psychologist/api/routes/health.py`
  - [x] `pytest tests/test_api.py tests/test_api_integration.py -q` (`11 skipped`, без падений)
  - [x] `pytest tests/test_admin_api.py -q` (`6 passed`)
  - [x] `pytest tests/smoke/test_pipeline_entrypoints.py tests/test_data_loader_fallback.py tests/test_stream_dependencies.py tests/unit/test_turn_diff_contract.py -q` (`13 passed`)
  - [x] Интегрированный целевой прогон API-контрактов:
    `pytest tests/test_admin_api.py tests/test_api.py tests/test_api_integration.py tests/smoke/test_pipeline_entrypoints.py tests/test_data_loader_fallback.py tests/test_stream_dependencies.py tests/unit/test_turn_diff_contract.py -q` (`19 passed, 11 skipped`)
  - [x] Полный прогон:
    `pytest -q --maxfail=1 --basetemp=.tmp_pytest_full` (`509 passed, 5 skipped`)

## Критерии готовности PRD-160.0
- [x] `from api.routes import router` работает без ошибок
- [x] `memory_v11.py` удален и не используется
- [x] README содержит предупреждение по CORS перед продом
- [x] `api/main.py` не менялся
