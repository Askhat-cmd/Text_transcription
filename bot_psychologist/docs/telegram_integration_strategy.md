# Telegram Integration Strategy

## Статус на 2026-04-25

- PRD-015A (Telegram Integration Contract) реализован.
- Включен только контрактный слой: без реального webhook/polling transport.
- По умолчанию Telegram отключен (`TELEGRAM_ENABLED=false`).

## Что уже реализовано

- Контрактный пакет: `api/telegram_adapter/`
  - `config.py` — feature flags (`TELEGRAM_ENABLED`, `TELEGRAM_MODE`, `TELEGRAM_BOT_TOKEN`)
  - `models.py` — `TelegramUpdateModel`, `TelegramAdapterResponse`
  - `adapter.py` — валидация и парсинг mock update payload
  - `service.py` — orchestration через Identity/Conversation services
  - `mocks/sample_updates.json` — примеры тестовых payload
- Dev-only endpoint:
  - `POST /api/v1/dev/telegram/mock-update`
  - доступ только с `dev-key-001`
- Стратегия strict linking:
  - непривязанный `telegram_user_id` возвращает controlled ответ `telegram_not_linked`
  - автоматический merge с web user не выполняется

## Целевой runtime-поток

1. Получить Telegram update (mock payload).
2. Преобразовать payload -> `TelegramUpdateModel`.
3. Вызвать `IdentityService.resolve_telegram(telegram_user_id)`.
4. При linked identity получить/создать conversation через `ConversationService` с `channel="telegram"`.
5. Передать текст в основной chat runtime.
6. Вернуть `TelegramAdapterResponse`.

## Что не входит в текущий этап

- Реальный Telegram Bot API transport.
- Webhook endpoint для Telegram.
- Polling worker.
- Реальный `/start <code>` linking flow.
- Delivery/retry исходящих сообщений в Telegram.

## Следующий этап (PRD-015B)

- Подключение реального transport слоя Telegram.
- Account linking flow `/start <code>`.
- Подтверждение эксплуатационных сценариев (ошибки transport, retry, мониторинг).
