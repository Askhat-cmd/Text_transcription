# Testing Matrix

## Цель

Единая матрица обязательных проверок перед merge для модулей identity/conversations и связанных API-контрактов.

## Обязательные наборы перед merge

### Набор A — identity + conversations + api

```bash
pytest tests/identity tests/conversations tests/api -q
```

Ожидание:
- PASS, без падений по ключевым сценариям резолва identity и lifecycle диалогов.

### Набор B — API sanity

```bash
pytest tests/api -q
```

Ожидание:
- PASS по HTTP-контрактам API.

### Набор C — Telegram contract (PRD-015A)

```bash
pytest tests/telegram_adapter/test_models.py tests/telegram_adapter/test_adapter.py tests/telegram_adapter/test_service.py tests/api/test_telegram_mock_routes.py -q
```

Ожидание:
- PASS по контрактам Telegram adapter (mock/dev-only).
- PASS по strict linking сценарию (`telegram_not_linked` для unlinked identity).

## Что относится к PRD-014

- `tests/conversations/*`
- `tests/identity/test_dependencies.py`
- `tests/identity/test_identity_repository.py`
- `tests/identity/test_identity_middleware.py`
- `tests/api/test_conversation_routes.py`
- `tests/api/test_dependencies_conversation.py`
- `tests/api/test_routes_identity_integration.py`
- `tests/api/test_admin_identity_endpoint.py`

## Ручные smoke-checks

После локального старта сервисов:

1. `GET /api/v1/health` -> `200`
2. `GET /api/v1/identity/me` -> `200`
3. `POST /api/v1/conversations/new` -> `200`
4. `GET /api/v1/conversations/` -> `200`
5. `POST /api/v1/questions/adaptive` -> `200`
6. `POST /api/v1/conversations/{id}/close` -> `200`

## Критерии pass/fail

### PASS
- Все обязательные тестовые наборы проходят;
- Нет падений критичных endpoint-ов;
- Ручные smoke-checks возвращают ожидаемые HTTP-коды.

### FAIL
- Любой red в наборах A/B;
- Любой red в наборе C (Telegram contract);
- Ошибки identity fallback, ломающие контракт UUID;
- Ошибки жизненного цикла conversations (создание/список/закрытие).

## Реализовано vs планируется

### Реализовано
- Базовая тест-матрица для PRD-014.
- Контрактные проверки PRD-015A (Telegram mock/dev flow).

### Планируется
- Выделение CI-пайплайна с обязательным gate для наборов A/B.
