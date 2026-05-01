# Testing Matrix

## Цель

Единая матрица обязательных проверок перед merge для identity/conversations, registration и Telegram transport.

## Набор A — Identity + Conversations + API

```bash
pytest tests/identity tests/conversations tests/api -q
```

Ожидание:
- PASS по резолву identity;
- PASS по lifecycle диалогов;
- PASS по API-контрактам уровня conversation/identity.

## Набор B — API sanity

```bash
pytest tests/api -q
```

Ожидание:
- PASS по HTTP-контрактам API.

## Набор C — Telegram adapter contract (mock/dev)

```bash
pytest tests/telegram_adapter/test_models.py tests/telegram_adapter/test_adapter.py tests/telegram_adapter/test_service.py tests/api/test_telegram_mock_routes.py -q
```

Ожидание:
- PASS по базовому Telegram mock flow;
- PASS по strict linking сценарию (`telegram_not_linked` для непривязанной identity).

## Registration package (PRD-016-v2)

| Тест-файл | Что проверяет | Команда |
|---|---|---|
| `tests/registration/test_security.py` | Argon2 hash/verify, токены и коды | `pytest tests/registration/test_security.py -q` |
| `tests/registration/test_guards.py` | `LinkAttemptGuard` (5 попыток / 15 минут) | `pytest tests/registration/test_guards.py -q` |
| `tests/registration/test_registration_models.py` | Pydantic-валидация username/полей | `pytest tests/registration/test_registration_models.py -q` |
| `tests/registration/test_repository.py` | CRUD профилей, invite keys, sessions, link codes | `pytest tests/registration/test_repository.py -q` |
| `tests/registration/test_registration_service.py` | register/login/link-flow и ошибки | `pytest tests/registration/test_registration_service.py -q` |
| `tests/registration/test_bootstrap.py` | идемпотентность `DatabaseBootstrap` | `pytest tests/registration/test_bootstrap.py -q` |
| `tests/registration/test_routes.py` | HTTP-контракты `/api/v1/auth/*` и `/api/v1/admin/invite-keys` | `pytest tests/registration/test_routes.py -q` |

## Telegram transport layer (PRD-015B-v2)

| Тест-файл | Что проверяет | Команда |
|---|---|---|
| `tests/telegram_adapter/test_outbound.py` | отправка исходящих сообщений и обработка ошибок Telegram API | `pytest tests/telegram_adapter/test_outbound.py -q` |
| `tests/telegram_adapter/test_transport.py` | polling loop, offset, retry/backoff, graceful stop | `pytest tests/telegram_adapter/test_transport.py -q` |
| `tests/telegram_adapter/test_webhook.py` | webhook-путь, проверка подписи и security guard | `pytest tests/telegram_adapter/test_webhook.py -q` |
| `tests/telegram_adapter/test_link_command.py` | `/link <code>` end-to-end на adapter-уровне | `pytest tests/telegram_adapter/test_link_command.py -q` |

## Полный пакетный прогон (Registration + Telegram transport)

```bash
pytest tests/registration tests/telegram_adapter/test_outbound.py tests/telegram_adapter/test_transport.py tests/telegram_adapter/test_webhook.py tests/telegram_adapter/test_link_command.py tests/api/test_telegram_mock_routes.py -q
```

Ожидаемый результат:
- PASS без регрессий в registration/Telegram transport;
- стабильный контракт `link-code -> confirm-link -> linked identity`.

## Ручные smoke-checks

После локального старта сервисов:

1. `GET /api/v1/health` -> `200`
2. `GET /api/v1/identity/me` -> `200`
3. `POST /api/v1/conversations/new` -> `200`
4. `GET /api/v1/conversations/` -> `200`
5. `POST /api/v1/questions/adaptive` -> `200`
6. `POST /api/v1/conversations/{id}/close` -> `200`
7. `POST /api/v1/auth/register` -> `200/409`
8. `POST /api/v1/auth/login` -> `200/401`
9. `POST /api/v1/auth/telegram/link-code` -> `200`
10. `POST /api/v1/auth/telegram/confirm-link` -> `200/400/403` (по входным условиям)

## Критерии PASS/FAIL

### PASS
- Все обязательные наборы A/B/C проходят;
- registration и Telegram transport тесты проходят;
- smoke-checks возвращают ожидаемые коды.

### FAIL
- Любой red в наборах A/B/C;
- red в registration/transport тестах;
- ошибки identity fallback, ломающие UUID-контракт;
- ошибки lifecycle диалогов (create/list/close/delete).
