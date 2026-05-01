# Telegram Integration Strategy

## Статус на 2026-05-01

- PRD-015A реализован: identity/conversation-контракт и strict linking.
- PRD-015B-v2 + PRD-016-v2 реализованы: transport-слой Telegram (`mock`, `polling`, `webhook`), регистрация и привязка.
- По умолчанию Telegram отключен в локальной среде (`TELEGRAM_ENABLED=false`), включается через env.

## Что уже реализовано

- Пакет `api/telegram_adapter/`:
  - `config.py` — feature flags и режимы запуска;
  - `models.py` — входные/выходные модели адаптера;
  - `adapter.py` — нормализация update и orchestration вызовов;
  - `service.py` — интеграция с Identity/Conversation и runtime;
  - `transport.py` — polling/webhook transport;
  - `outbound.py` — отправка сообщений в Telegram API;
  - `routes.py` — HTTP-маршруты для webhook/mock.
- Dev endpoint: `POST /api/v1/dev/telegram/mock-update` (доступ с `dev-key-001`).
- Привязка Telegram:
  - `POST /api/v1/auth/telegram/link-code` (Bearer session token),
  - `POST /api/v1/auth/telegram/confirm-link` (internal key + HMAC).
- Безопасность:
  - `X-Internal-Key` + `X-Request-HMAC` для `confirm-link`;
  - `LinkAttemptGuard` ограничивает brute-force по коду.

## Целевой runtime-поток

1. Принять Telegram update (webhook/polling/mock).
2. Преобразовать payload в `TelegramUpdateModel`.
3. Резолвить identity по `telegram_user_id`.
4. Для linked identity получить/создать conversation с `channel="telegram"`.
5. Передать сообщение в runtime (`/api/v1/questions/adaptive` логика).
6. Вернуть/отправить ответ в Telegram.

## Ограничения текущего этапа

- Full production hardening (алерты, расширенный аудит, эксплуатационные SLO) не финализированы.
- Для production необходимы:
  - отдельный секрет-менеджмент;
  - строгий контроль webhook URL и TLS;
  - централизованный мониторинг ошибок transport/outbound.

## Рекомендуемые проверки

```bash
pytest tests/telegram_adapter/test_models.py tests/telegram_adapter/test_adapter.py tests/telegram_adapter/test_service.py tests/api/test_telegram_mock_routes.py -q
pytest tests/telegram_adapter/test_outbound.py tests/telegram_adapter/test_transport.py tests/telegram_adapter/test_webhook.py tests/telegram_adapter/test_link_command.py -q
```
