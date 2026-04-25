# TASKLIST_PRD-015A_Telegram_Integration_Contract_PROGRESS

## Контекст
- PRD: `PRD-015A_Telegram_Integration_Contract_2026-04-25.md`
- Цель: внедрить контракт Telegram-интеграции без реального transport/webhook.
- Режим: strict linking (`telegram_not_linked` для непривязанного telegram_user_id).

## Задачи

- [x] T1: Стандартизировать модуль `bot_psychologist/api/telegram_adapter/`
- [x] T2: Добавить feature-flags конфиг (`TELEGRAM_ENABLED`, `TELEGRAM_MODE`, `TELEGRAM_BOT_TOKEN`)
- [x] T3: Добавить модели `TelegramUpdateModel` и `TelegramAdapterResponse`
- [x] T4: Реализовать `TelegramUpdateAdapter` (dict/json -> модель + валидация)
- [x] T5: Реализовать `TelegramAdapterService` через DI (`IdentityService`, `ConversationService`, chat executor)
- [x] T6: Добавить mock payloads `api/telegram_adapter/mocks/sample_updates.json`
- [x] T7: Добавить dev-only endpoint `POST /api/v1/dev/telegram/mock-update`
- [x] T8: Ограничить endpoint dev-key (`dev-key-001`) и controlled errors
- [x] T9: Добавить unit/api тесты telegram adapter
- [x] T10: Обновить README/docs по Telegram contract (без утверждений про production)

## Тесты

- [x] `pytest bot_psychologist/tests/telegram_adapter/test_models.py -q`
- [x] `pytest bot_psychologist/tests/telegram_adapter/test_adapter.py -q`
- [x] `pytest bot_psychologist/tests/telegram_adapter/test_service.py -q`
- [x] `pytest bot_psychologist/tests/api/test_telegram_mock_routes.py -q`
- [x] `pytest bot_psychologist/tests/identity bot_psychologist/tests/conversations bot_psychologist/tests/api -q`

## Чеки качества

- [x] В `api/telegram_adapter/` нет прямых SQL-запросов
- [x] Нет прямых импортов `api/identity/repository.py` и `api/conversations/repository.py` из adapter-layer
- [x] Telegram disabled по умолчанию
- [x] При unlinked telegram user возвращается `telegram_not_linked`
- [x] При linked user используется `channel='telegram'` и возвращается `conversation_id`
- [x] Текущий runtime `bot_psychologist` не сломан

## Прогресс
- 2026-04-25: tasklist создан, старт реализации.
- 2026-04-25: устранен конфликт импортов с верхнеуровневым `telegram_adapter` (модуль перенесен в `api/telegram_adapter`).
- 2026-04-25: тесты PRD-015A — `9 passed`.
- 2026-04-25: regression-пакет `tests/identity tests/conversations tests/api` — `70 passed`.
