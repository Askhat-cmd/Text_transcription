# Registration и Access Control

## 1. Overview

Пакет `api/registration/` отвечает за регистрацию, логин, сессии доступа и безопасную привязку Telegram-аккаунта к существующему `user_id`.

Место в архитектуре:
- `api/identity/` хранит канонического пользователя и связанные внешние идентичности;
- `api/registration/` управляет доступом (`username`, `access_key`, `session_token`, `invite_key`, `link_code`);
- `api/telegram_adapter/` использует registration-контракт для подтвержденной привязки Telegram.

## 2. User Registration Flow

```text
register (username + invite_key)
  -> create user_profile + access_key
  -> consume invite_key
  -> return user_id + access_key

login (username + access_key)
  -> verify access_key (argon2)
  -> issue session_token (expires_at)

telegram/link-code (Bearer session_token)
  -> issue one-time code (TTL 900 sec)

telegram/confirm-link (internal-only)
  -> verify X-Internal-Key + X-Request-HMAC
  -> resolve code
  -> create linked_identity(provider=telegram, external_id=telegram_user_id)
  -> return linked user_id
```

## 3. API Endpoints

### POST `/api/v1/auth/register`

Назначение: регистрация пользователя по `username + invite_key`.

Request body:
```json
{
  "username": "alex_neo",
  "invite_key": "BP-INVITE-..."
}
```

Response:
```json
{
  "user_id": "uuid",
  "access_key": "BP-ACCESS-...",
  "role": "user"
}
```

Ошибки:
- `400` invalid/expired/used invite key
- `409` username already exists

### POST `/api/v1/auth/login`

Назначение: вход по `username + access_key`.

Request body:
```json
{
  "username": "alex_neo",
  "access_key": "BP-ACCESS-..."
}
```

Response:
```json
{
  "user_id": "uuid",
  "session_token": "token",
  "role": "user",
  "username": "alex_neo",
  "expires_at": "2026-05-01T12:00:00+00:00"
}
```

Ошибки:
- `401` invalid credentials
- `403` blocked/inactive user

### POST `/api/v1/auth/telegram/link-code`

Назначение: выдать одноразовый код для привязки Telegram.

Headers:
- `Authorization: Bearer <session_token>`

Response:
```json
{
  "code": "ABCD1234",
  "expires_in_seconds": 900
}
```

Ошибки:
- `401` invalid/expired session token

### POST `/api/v1/auth/telegram/confirm-link`

Назначение: internal endpoint подтверждения привязки Telegram.

Headers:
- `X-Internal-Key: <internal key>`
- `X-Request-HMAC: <sha256 hmac>`

Request body:
```json
{
  "code": "ABCD1234",
  "telegram_user_id": "123456789"
}
```

Response:
```json
{
  "ok": true,
  "user_id": "uuid",
  "username": "alex_neo"
}
```

Ошибки:
- `403` invalid internal key / invalid request signature
- `400` invalid/expired/used code

### POST `/api/v1/admin/invite-keys`

Назначение: создать invite key.

Headers:
- `Authorization: Bearer <admin session_token>`

Request body:
```json
{
  "role_grant": "user",
  "expires_in_days": 7
}
```

Response:
```json
{
  "key_value": "BP-INVITE-...",
  "expires_at": "2026-05-08T12:00:00+00:00"
}
```

Ошибки:
- `401` invalid/expired session token
- `403` admin role required

## 4. Roles & Access

Основные роли профиля:
- `admin`
- `user`
- `trial`
- `blocked`

Технические роли в моделях и служебных сценариях:
- `dev`
- `test`
- `internal`
- `anonymous`

Доступ:
- register/login/link-code: пользовательский контур (`/api/v1/auth/*`);
- confirm-link: только internal контур (`X-Internal-Key` + `X-Request-HMAC`);
- invite-keys: только `admin` через Bearer session token.

## 5. Security

- Для `access_key` используется Argon2 (`pwdlib`), а не простой `sha256`.
- `LinkAttemptGuard`: 5 попыток / 15 минут на `telegram_user_id`.
- `/telegram/confirm-link` не принимает `dev-key`; требуется `X-Internal-Key` + `X-Request-HMAC`.

## 6. DatabaseBootstrap

На старте `DatabaseBootstrap`:
- гарантирует схему registration-таблиц;
- сидирует API keys (`dev-key-001`, `test-key-001`, `internal-telegram-key`, с учетом env override);
- может создать первого admin-пользователя при наличии `ADMIN_USERNAME` + `ADMIN_INVITE_KEY`.

Режим идемпотентный: повторный запуск не ломает существующие данные.

## 7. Module Structure

`api/registration/`:
- `models.py` — pydantic-модели request/response.
- `repository.py` — SQL-операции профилей, сессий, invite keys, link codes.
- `service.py` — доменная логика register/login/link/roles.
- `routes.py` — HTTP-эндпоинты `/api/v1/auth/*` и `/api/v1/admin/invite-keys`.
- `security.py` — генерация и проверка ключей/кодов.
- `guards.py` — защитные лимиты (`LinkAttemptGuard`).
- `bootstrap.py` — инициализация и seed-данные.

## 8. Related Tests

Registration:
- `tests/registration/test_security.py`
- `tests/registration/test_guards.py`
- `tests/registration/test_registration_models.py`
- `tests/registration/test_repository.py`
- `tests/registration/test_registration_service.py`
- `tests/registration/test_bootstrap.py`
- `tests/registration/test_routes.py`

Telegram transport / linking:
- `tests/telegram_adapter/test_outbound.py`
- `tests/telegram_adapter/test_transport.py`
- `tests/telegram_adapter/test_webhook.py`
- `tests/telegram_adapter/test_link_command.py`
- `tests/api/test_telegram_mock_routes.py`
